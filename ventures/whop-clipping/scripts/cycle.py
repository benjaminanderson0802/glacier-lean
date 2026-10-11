"""One auditable Scout → clip → YouTube → Whop cycle. Dry-run is the default."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import random
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__:
    from .clipper import candidate_segments, make_clip, transcribe
    from .interfaces import Campaign, Clip, Post
    from .ledger import Ledger, clip_home
    from .sources import fetch_source
    from .variants import assign_segments, make_variant
else:  # direct script execution from a Glacier command node
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.clipper import candidate_segments, make_clip, transcribe
    from scripts.interfaces import Campaign, Clip, Post
    from scripts.ledger import Ledger, clip_home
    from scripts.sources import fetch_source
    from scripts.variants import assign_segments, make_variant


DEFAULT_CHANNELS = [
    "@frameandmomentdesk", "@highlightdesknotes", "@replaynotesdesk", "@quickreplaydesk",
    "@dailycutnotes", "@clipcurrentdesk", "@sceneselectnotes", "@momentarchivedesk",
    "@thecliproomnotes", "@contextclipsdesk",
]


class FakeScout:
    def __init__(self, campaigns=()):
        self.campaigns = list(campaigns)

    def list_campaigns(self):
        return list(self.campaigns)


class FakeUploader:
    def __init__(self):
        self.uploads = []

    def upload(self, clip, *, dry_run=False):
        self.uploads.append((clip, dry_run))
        return Post(clip.id, clip.channel_handle, "youtube_shorts", f"fake-{clip.id}",
                    f"https://example.invalid/{clip.id}", datetime.now(timezone.utc).isoformat())

    def refresh_statuses(self):
        return []


class FakeSubmitter:
    def __init__(self):
        self.submissions = []

    def submit(self, campaign, post, *, dry_run=False):
        self.submissions.append((campaign, post, dry_run))
        return f"fake-submission-{post.clip_id}"

    def refresh_statuses(self):
        return []


def load_plugin(spec: str, *, config=None):
    if not spec or "." not in spec:
        raise ValueError("plugin must be configured as module.ClassName")
    module_name, class_name = spec.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), class_name)
    try:
        return cls(config=config)
    except TypeError:
        return cls()


def _campaign(value):
    if isinstance(value, Campaign):
        return value
    data = dict(value)
    return Campaign(**data)


def _campaign_eligible(campaign, config, ledger):
    platforms = {str(value).lower().replace(" ", "_") for value in campaign.platforms}
    youtube = bool(platforms & {"youtube", "youtube_shorts", "shorts"})
    rules = campaign.rules_text.lower()
    if re.search(r"(?:youtube(?: shorts)?).{0,35}(?:not allowed|prohibited|forbidden|excluded)|(?:no|do not use|don't use)\s+youtube", rules):
        youtube = False
    allowed_line = re.search(r"(?:allowed|eligible) platforms?\s*[:=]\s*([^\n.]+)", rules)
    if allowed_line and not re.search(r"youtube|shorts", allowed_line.group(1), re.I):
        youtube = False
    if not youtube or campaign.cpm_usd <= 0:
        return False
    if campaign.budget_left_usd is not None and campaign.budget_left_usd <= 0:
        return False
    if campaign.id in set(config.get("paused_campaign_ids", [])):
        return False
    approved = set(config.get("approved_campaign_ids", []))
    if campaign.id not in approved:
        return False
    return not all(ledger.is_paused(channel, campaign.id) for channel in config.get("channels", DEFAULT_CHANNELS))


def _source_id(campaign_id, url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def _rule_length(rules_text, kind, default):
    match = re.search(rf"\b{kind}\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\b",
                      rules_text, re.I)
    return float(match.group(1)) if match else default


def _no_edit_required(campaign):
    return campaign.requires_editing is False or bool(re.search(
        r"no editing (?:is )?required|do not edit|don't edit|post (?:the )?provided clip as[- ]is",
        campaign.rules_text, re.I))


def _media_duration(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required to confirm provided no-edit clip duration")
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                            check=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
    return float(result.stdout.strip())


def _prepare_clips(campaign, config, ledger, home):
    output = []
    source_cfg = config.get("sources", {})
    for source_item in campaign.source_links:
        url = source_item.get("url") if isinstance(source_item, dict) else str(source_item)
        source_id = str(source_item.get("id")) if isinstance(source_item, dict) and source_item.get("id") else _source_id(campaign.id, url)
        source = fetch_source(url, source_id, cache_dir=home / "media" / "sources", ledger=ledger,
                              max_bytes=int(source_cfg.get("max_bytes", 2_000_000_000)),
                              timeout_s=int(source_cfg.get("timeout_s", 1800)))
        source_id = source.provenance["sha256"][:20]
        ledger.record_source(source_id, source.url, source.path, source.provenance["sha256"],
                             {**source.provenance, "canonical_source_id": source_id})
        ledger.event("source_fetched", {"campaign_id": campaign.id, "source_id": source_id,
                                         "path": str(source.path), "cached": source.cached}, f"source:{source_id}")
        if _no_edit_required(campaign):
            duration = _media_duration(source.path)
            minimum = _rule_length(campaign.rules_text, r"min(?:imum)?", 0)
            maximum = _rule_length(campaign.rules_text, r"max(?:imum)?", float("inf"))
            if duration < minimum or duration > maximum:
                ledger.event("no_edit_clip_out_of_rules", {"campaign_id": campaign.id,
                    "source_id": source_id, "duration_s": duration, "minimum_s": minimum, "maximum_s": maximum})
                continue
            segments = [{"source_id": source_id, "start_s": 0.0, "end_s": duration, "text": campaign.name,
                         "words": [], "score": 1.0, "passthrough": True}]
        else:
            transcript, metadata = transcribe(source.path, model_size=config.get("transcription", {}).get("model", "small"))
            ledger.event("transcribed", {"source_id": source_id, **metadata}, f"transcribed:{source_id}")
            minimum = max(20, _rule_length(campaign.rules_text, r"min(?:imum)?", 20))
            maximum = min(58, _rule_length(campaign.rules_text, r"max(?:imum)?", 58))
            segments = candidate_segments(transcript, source_id, campaign.rules_text, min_s=minimum, max_s=maximum,
                                          llm_url=config.get("ollama_url", "http://127.0.0.1:11434"))
        channels = [channel for channel in config.get("channels", DEFAULT_CHANNELS)
                    if not ledger.is_paused(channel, campaign.id)]
        assignments = assign_segments(segments, channels, ledger)
        for item in assignments:
            variant = make_variant(campaign, item, item["channel_handle"])
            clip_digest = hashlib.sha256(f"{campaign.id}:{source_id}:{item['start_s']:.3f}:{item['end_s']:.3f}".encode()).hexdigest()[:24]
            target = home / "media" / "clips" / f"{clip_digest}.mp4"
            if not target.exists():
                if item.get("passthrough"):
                    make_clip(source.path, target, item, requires_editing=False)
                else:
                    make_clip(source.path, target, item, requires_editing=True,
                              caption_words=config.get("captions", True), mode=config.get("video_layout", "blurred_background"),
                              caption_style=variant["caption_style"])
            clip = Clip(clip_digest, campaign.id, source_id, item["start_s"], item["end_s"], str(target),
                        variant["title"], variant["description"], variant["hashtags"], item["channel_handle"])
            ledger.record_clip(clip)
            output.append(clip)
    return output


def _is_strike_or_terms_error(error):
    text = str(error).lower()
    return any(token in text for token in ("strike", "terms violation", "terms error", "account suspended", "channel terminated"))


def _refresh_statuses(plugin, kind, ledger, *, collapse_ratio=0.2):
    refresh = getattr(plugin, "refresh_statuses", None)
    if not callable(refresh):
        return
    try:
        statuses = refresh()
    except Exception as exc:
        ledger.event(f"{kind}_refresh_error", {"error": str(exc)})
        return
    for item in statuses or []:
        if kind == "whop":
            ledger.record_submission(item["campaign_id"], item["clip_id"], item["submission_id"],
                                     item.get("status", "unknown"), item.get("reason", ""))
            if str(item.get("status", "")).lower() == "flagged" or "flagged" in str(item.get("reason", "")).lower():
                clip = item.get("clip")
                channel = item.get("channel_handle") or (clip.channel_handle if clip else "")
                if channel:
                    ledger.pause(channel, item["campaign_id"], "Whop marked submission flagged: " + item.get("reason", ""))
        elif kind == "youtube" and item.get("views_collapsed"):
            ledger.pause(item["channel_handle"], None, "channel views collapsed")
        elif kind == "youtube":
            error = item.get("error") or item.get("status") or ""
            if _is_strike_or_terms_error(error):
                ledger.pause(item["channel_handle"], None, f"YouTube strike/terms error: {error}")
            elif "views" in item and item.get("channel_handle"):
                collapsed = ledger.record_views(item["channel_handle"], str(item.get("video_id", "unknown")),
                                                 item["views"], collapse_ratio=item.get(
                                                     "collapse_ratio", collapse_ratio))
                if collapsed:
                    ledger.event("views_collapse_detected", {"channel": item["channel_handle"],
                                                              "video_id": item.get("video_id"),
                                                              "views": item["views"]})


def run_cycle(config, *, home=None, scout=None, uploader=None, submitter=None, dry_run=True,
              campaign_clips=None, sleep_fn=time.sleep, now_fn=lambda: datetime.now(timezone.utc), rng=None):
    home = clip_home(home)
    ledger = Ledger(home)
    rng = rng or random.Random()
    if not dry_run and not config.get("live", False):
        raise RuntimeError("live run refused: set live=true in the private config after owner setup")
    plugins = config.get("plugins", {})
    if scout is None:
        try:
            scout = load_plugin(plugins.get("scout", "whop_scout.WhopScout"), config=config)
        except (ImportError, AttributeError, ValueError) as exc:
            if not dry_run:
                raise
            scout = FakeScout()
            ledger.event("plugin_unavailable", {"plugin": "scout", "error": str(exc)})
    if uploader is None:
        try:
            uploader = load_plugin(plugins.get("uploader", "youtube_upload.YouTubeUploader"), config=config)
        except (ImportError, AttributeError, ValueError) as exc:
            if not dry_run:
                raise
            uploader = FakeUploader()
            ledger.event("plugin_unavailable", {"plugin": "uploader", "error": str(exc)})
    if submitter is None:
        try:
            submitter = load_plugin(plugins.get("submitter", "whop_submit.WhopSubmitter"), config=config)
        except (ImportError, AttributeError, ValueError) as exc:
            if not dry_run:
                raise
            submitter = FakeSubmitter()
            ledger.event("plugin_unavailable", {"plugin": "submitter", "error": str(exc)})
    channels = config.get("channels", DEFAULT_CHANNELS)
    per_channel_cap = max(0, int(config.get("daily_channel_cap", 3)))
    global_cap = min(100, max(0, int(config.get("global_daily_cap", 100))))
    min_spacing = timedelta(hours=max(2.0, float(config.get("min_spacing_hours", 2))))
    results = {"dry_run": dry_run, "campaigns": 0, "clips": 0, "uploads": 0, "submissions": 0, "skipped": 0}
    ledger.event("cycle_started", {"dry_run": dry_run, "channels": channels})
    seen_clip_ids = set()
    try:
        ledger.event("scout_started", {})
        campaigns = [_campaign(item) for item in scout.list_campaigns()]
        for campaign in campaigns:
            ledger.record_campaign(campaign)
        eligible = [item for item in campaigns if _campaign_eligible(item, config, ledger)]
        eligible.sort(key=lambda item: (item.cpm_usd, item.budget_left_usd or 0), reverse=True)
        results["campaigns"] = len(eligible)
        ledger.event("campaigns_selected", {"campaign_ids": [item.id for item in eligible]})
        for campaign in eligible:
            ledger.event("campaign_started", {"campaign_id": campaign.id})
            clips = list(campaign_clips[campaign.id]) if campaign_clips is not None else _prepare_clips(campaign, config, ledger, home)
            results["clips"] += len(clips)
            for clip in clips:
                if clip.id in seen_clip_ids:
                    ledger.event("duplicate_clip_skipped", {"clip_id": clip.id, "channel": clip.channel_handle})
                    results["skipped"] += 1
                    continue
                seen_clip_ids.add(clip.id)
                if clip.channel_handle not in channels or ledger.is_paused(clip.channel_handle, campaign.id):
                    results["skipped"] += 1
                    continue
                ledger.record_clip(clip)
                if ledger.segment_conflicts(clip.source_id, clip.start_s, clip.end_s,
                                            channel_handle=clip.channel_handle, except_clip_id=clip.id):
                    ledger.event("overlapping_segment_skipped", {"clip_id": clip.id, "channel": clip.channel_handle})
                    results["skipped"] += 1
                    continue
                if ledger.submitted_or_posted(clip.id):
                    results["skipped"] += 1
                    continue
                now = now_fn()
                day = now.date().isoformat()
                if ledger.posts_today(clip.channel_handle, day) >= per_channel_cap or ledger.global_posts_today(day) >= global_cap:
                    ledger.event("upload_cap_reached", {"channel": clip.channel_handle, "campaign_id": campaign.id})
                    results["skipped"] += 1
                    continue
                if dry_run:
                    ledger.event("upload_planned", {"clip_id": clip.id, "channel": clip.channel_handle,
                                                     "campaign_id": campaign.id}, f"planned:{clip.id}")
                    results["skipped"] += 1
                    continue
                if campaign.id not in set(config.get("approved_campaign_ids", [])):
                    ledger.event("campaign_not_owner_approved", {"campaign_id": campaign.id})
                    results["skipped"] += 1
                    continue
                previous = ledger.last_post_at(clip.channel_handle)
                jitter = max(0, int(config.get("posting_jitter_minutes", 45)))
                delay = rng.randint(0, jitter * 60) if jitter else 0
                scheduled = now + timedelta(seconds=delay)
                if previous and scheduled < previous + min_spacing:
                    scheduled = previous + min_spacing
                if scheduled.date() != now.date():
                    ledger.event("upload_deferred", {"clip_id": clip.id, "scheduled_at": scheduled.isoformat()})
                    results["skipped"] += 1
                    continue
                wait_s = max(0.0, (scheduled - now).total_seconds())
                if wait_s:
                    ledger.event("upload_wait", {"clip_id": clip.id, "seconds": int(wait_s), "scheduled_at": scheduled.isoformat()})
                    sleep_fn(wait_s)
                ledger.event("upload_started", {"clip_id": clip.id, "channel": clip.channel_handle})
                try:
                    post = uploader.upload(clip, dry_run=False)
                except Exception as exc:
                    ledger.event("upload_failed", {"clip_id": clip.id, "error": str(exc)})
                    if _is_strike_or_terms_error(exc):
                        ledger.pause(clip.channel_handle, None, f"YouTube strike/terms error: {exc}")
                    continue
                if post.channel_handle != clip.channel_handle or post.clip_id != clip.id:
                    raise RuntimeError("uploader returned a post for a different clip or channel")
                ledger.record_post(post)
                results["uploads"] += 1
                ledger.event("submit_started", {"campaign_id": campaign.id, "clip_id": clip.id})
                try:
                    submission_id = submitter.submit(campaign, post, dry_run=False)
                except Exception as exc:
                    ledger.event("submit_failed", {"campaign_id": campaign.id, "clip_id": clip.id, "error": str(exc)})
                    continue
                ledger.record_submission(campaign.id, clip.id, submission_id, "submitted", "")
                results["submissions"] += 1
        _refresh_statuses(submitter, "whop", ledger)
        _refresh_statuses(uploader, "youtube", ledger,
                          collapse_ratio=float(config.get("view_collapse_ratio", 0.2)))
        ledger.event("cycle_completed", results)
        return results
    except Exception as exc:
        ledger.event("cycle_failed", {"error": str(exc), "results": results})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a Whop clipping cycle (dry-run by default)")
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("CLIP_HOME", Path.home() / ".glacier/ventures/whop-clipping")) / "config.json")
    parser.add_argument("--dry-run", action="store_true", default=True, help="plan the cycle without uploading (default)")
    parser.add_argument("--live", action="store_true", help="perform uploads/submissions only when config live=true")
    parser.add_argument("--home", type=Path, default=None)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    # Scheduled Glacier flows pass --live; config remains the final live switch.
    effective_dry_run = not args.live or not config.get("live", False)
    output = run_cycle(config, home=args.home, dry_run=effective_dry_run)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
