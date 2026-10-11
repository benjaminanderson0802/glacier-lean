"""Campaign discovery, rules review, clip production, independent QA and library stocking."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .cycle import DEFAULT_CHANNELS, FakeScout, _campaign, _campaign_eligible, load_plugin
from .interfaces import Campaign, Clip
from .ledger import Ledger, clip_home
from .clipper import candidate_segments, make_clip, transcribe
from .sources import fetch_source
from .variants import assign_segments, make_variant
from .variants import channel_style


def parse_campaign_requirements(rules_text: str) -> dict:
    tags = list(dict.fromkeys(re.findall(r"(?<!\w)#[\w-]+", rules_text)))
    disclosures = []
    mentions = list(dict.fromkeys(re.findall(r"(?<!\w)@[\w.-]+", rules_text)))
    links = list(dict.fromkeys(re.findall(r"https?://[^\s,)]+", rules_text)))
    for line in rules_text.splitlines():
        match = re.search(r"(?:disclosure|must say|caption must)\s*[:=]?\s*(.+)", line, re.I)
        if match:
            disclosures.append(match.group(1).strip())
    min_match = re.search(r"\bmin(?:imum)?(?:imum)?\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)", rules_text, re.I)
    max_match = re.search(r"\bmax(?:imum)?(?:imum)?\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)", rules_text, re.I)
    edits_match = re.search(r"allowed edits?\s*[:=]\s*([^\n]+)", rules_text, re.I)
    banned_match = re.search(r"banned content\s*[:=]\s*([^\n]+)", rules_text, re.I)
    no_edit = bool(re.search(r"no editing|do not edit|don't edit|unedited|as[- ]is", rules_text, re.I))
    if re.search(r"no editing\s*[:=]\s*(?:false|no|0)", rules_text, re.I):
        no_edit = False
    return {"required_tags": tags, "disclosures": list(dict.fromkeys(disclosures)), "mentions": mentions,
            "links": links, "min_length_s": float(min_match.group(1)) if min_match else 0.0,
            "max_length_s": float(max_match.group(1)) if max_match else 58.0,
            "allowed_edits": [part.strip() for part in re.split(r"[,;]", edits_match.group(1))] if edits_match else [],
            "banned_content": [part.strip() for part in re.split(r"[,;]", banned_match.group(1))] if banned_match else [],
            "no_edit": no_edit}


def qa_clip(clip: Clip, checklist: dict, *, word_times=(), probe_fn=None) -> list[str]:
    failures = []
    if not Path(clip.path).is_file():
        failures.append("rendered clip file is missing")
    duration = clip.end_s - clip.start_s
    if duration < float(checklist.get("min_length_s", 0)) or duration > float(checklist.get("max_length_s", 58)):
        failures.append("length outside campaign limits")
    metadata = "\n".join([clip.title, clip.description, *clip.hashtags])
    missing = [tag for tag in checklist.get("required_tags", []) if tag.lower() not in metadata.lower()]
    if missing:
        failures.append("required tags missing from clip metadata: " + ", ".join(missing))
    for required in [*checklist.get("disclosures", []), *checklist.get("mentions", []), *checklist.get("links", [])]:
        if required.lower() not in metadata.lower():
            failures.append("campaign requirement missing from metadata: " + required)
    spoken = " ".join(str(word.get("word", "")) for word in word_times)
    for banned in checklist.get("banned_content", []):
        if banned and re.search(rf"\b{re.escape(banned.strip())}\b", spoken + " " + metadata, re.I):
            failures.append("banned campaign content detected: " + banned)
    if checklist.get("no_edit") and not clip.passthrough:
        failures.append("campaign prohibits editing but clip is not an untouched pass-through")
    for word in word_times:
        if float(word["start"]) < -0.05 or float(word["end"]) > duration + 0.05:
            failures.append("caption word timestamp outside audio by over 50 ms")
            break
        if float(word["end"]) < float(word["start"]):
            failures.append("caption word timestamp is inverted")
            break
    if not clip.passthrough and not word_times:
        failures.append("word-level caption timing is missing")
    if probe_fn:
        media = probe_fn(clip.path)
        if media is None:
            failures.append("media QA tools are unavailable")
        elif media.get("width") != 1080 or media.get("height") != 1920:
            failures.append("render is not 1080x1920")
        if media is not None and not media.get("audio_loudness_ok", False):
            failures.append("audio loudness outside target")
    return failures


def _ffprobe(path):
    binary = shutil.which("ffprobe")
    if not binary:
        return None
    result = subprocess.run([binary, "-v", "error", "-show_streams", "-of", "json", path],
                            check=True, capture_output=True, text=True, timeout=30)
    streams = json.loads(result.stdout).get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    loudness_ok = False
    ffmpeg = shutil.which("ffmpeg")
    if audio and ffmpeg:
        measure = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true",
                                  "-f", "null", "-"], capture_output=True, text=True, timeout=120)
        values = re.findall(r"\bI:\s*(-?\d+(?:\.\d+)?)\s*LUFS", measure.stderr)
        if values:
            loudness_ok = -18.0 <= float(values[-1]) <= -14.0
    return {"width": video.get("width"), "height": video.get("height"),
            "audio_loudness_ok": loudness_ok, "audio_codec": audio.get("codec_name")}


def _rule_length(rules_text, kind, default):
    match = re.search(rf"\b{kind}\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\b",
                      rules_text, re.I)
    return float(match.group(1)) if match else default


def _no_edit_required(campaign):
    checklist = parse_campaign_requirements(campaign.rules_text)
    return campaign.requires_editing is False or checklist["no_edit"]


def _media_duration(path):
    binary = shutil.which("ffprobe")
    if not binary:
        raise RuntimeError("ffprobe is required to confirm provided no-edit clip duration")
    result = subprocess.run([binary, "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                            check=True, capture_output=True, text=True, timeout=30)
    return float(result.stdout.strip())


def _source_id(campaign_id, url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def _campaign_sources(campaign, home):
    """Choose source links in order and label their provenance."""
    if campaign.source_links:
        return [{**(item if isinstance(item, dict) else {"url": str(item)}),
                 "route": "public_detail_page"} for item in campaign.source_links]

    youtube_urls = list(dict.fromkeys(re.findall(
        r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?[^\s<>]+|shorts/[^\s<>]+|"
        r"channel/[^\s<>]+|@[^ \s<>]+)|youtu\.be/[^\s<>]+)",
        campaign.rules_text, re.I,
    )))
    if youtube_urls:
        return [{"url": url.rstrip(".,);]"), "route": "campaign_rules_or_description"}
                for url in youtube_urls]

    override = home / "campaign_sources" / f"{campaign.id}.txt"
    if override.is_file():
        urls = []
        for line in override.read_text(encoding="utf-8").splitlines():
            value = line.split("#", 1)[0].strip()
            if value.startswith(("https://", "http://")):
                urls.append(value)
        return [{"url": url, "route": "campaign_override"} for url in dict.fromkeys(urls)]
    return []


def _prepare_clips(campaign, config, ledger, home):
    output = []
    source_cfg = config.get("sources", {})
    checklist = parse_campaign_requirements(campaign.rules_text)
    recovered = []
    for row in ledger.campaign_clips(campaign.id):
        library_item = ledger.library_item(row["id"])
        if library_item and library_item["status"] in {"ready", "posted"}:
            continue
        if Path(row.get("path", "")).is_file():
            recovered.append(Clip(**row))
    if recovered:
        return recovered
    for source_item in _campaign_sources(campaign, home):
        url = source_item.get("url") if isinstance(source_item, dict) else str(source_item)
        source_route = source_item.get("route", "public_detail_page") if isinstance(source_item, dict) else "public_detail_page"
        source_id = str(source_item.get("id")) if isinstance(source_item, dict) and source_item.get("id") else _source_id(campaign.id, url)
        source = fetch_source(url, source_id, cache_dir=home / "media" / "sources", ledger=ledger,
                              max_bytes=int(source_cfg.get("max_bytes", 2_000_000_000)),
                              timeout_s=int(source_cfg.get("timeout_s", 1800)))
        source_id = source.provenance["sha256"][:20]
        ledger.record_source(source_id, source.url, source.path, source.provenance["sha256"],
                             {**source.provenance, "canonical_source_id": source_id,
                              "campaign_id": campaign.id, "source_route": source_route})
        ledger.event("campaign_source_selected", {
            "campaign_id": campaign.id, "source_id": source_id,
            "url": source.url, "route": source_route,
        }, f"campaign-source-selected:{campaign.id}:{source_id}")
        if _no_edit_required(campaign):
            duration = _media_duration(source.path)
            minimum, maximum = checklist["min_length_s"], checklist["max_length_s"]
            transcript, metadata = transcribe(source.path, model_size=config.get("transcription", {}).get("model", "small"))
            ledger.event("transcribed_no_edit_source", {"source_id": source_id, **metadata}, f"transcribed-no-edit:{source_id}")
            words = [word for row in transcript for word in row.get("words", [])]
            segments = ([{"source_id": source_id, "start_s": 0.0, "end_s": duration,
                          "text": " ".join(str(word.get("word", "")) for word in words),
                          "words": words, "score": 1.0, "passthrough": True}]
                        if minimum <= duration <= maximum else [])
        else:
            transcript, metadata = transcribe(source.path, model_size=config.get("transcription", {}).get("model", "small"))
            ledger.event("transcribed", {"source_id": source_id, **metadata}, f"transcribed:{source_id}")
            minimum = max(20, checklist["min_length_s"] or 20)
            maximum = min(58, checklist["max_length_s"])
            segments = candidate_segments(transcript, source_id, campaign.rules_text, min_s=minimum, max_s=maximum,
                                          llm_url=config.get("ollama_url", "http://127.0.0.1:11434"))
        channels = [channel for channel in config.get("channels", ["__library__"])
                    if not ledger.is_paused(channel, campaign.id)]
        assignments = assign_segments(segments, channels, ledger)
        for item in assignments:
            variant = make_variant(campaign, item, item["channel_handle"])
            digest = hashlib.sha256(f"{campaign.id}:{source_id}:{item['start_s']:.3f}:{item['end_s']:.3f}".encode()).hexdigest()[:24]
            target = home / "media" / "clips" / f"{digest}.mp4"
            render_started = time.monotonic()
            rendered = not target.exists()
            previous = ledger.clip(digest) if not rendered else None
            if not target.exists():
                make_clip(source.path, target, item, requires_editing=not item.get("passthrough", False),
                          caption_words=False, mode=config.get("video_layout", "blurred_background"))
            render_seconds = (time.monotonic() - render_started if rendered else
                              float((previous or {}).get("render_seconds", 0.0)))
            words = [{**word, "start": max(0.0, float(word["start"])-float(item["start_s"])),
                      "end": min(float(item["end_s"])-float(item["start_s"]), float(word["end"])-float(item["start_s"]))}
                     for word in item.get("words", [])]
            clip = Clip(digest, campaign.id, source_id, item["start_s"], item["end_s"], str(target),
                        variant["title"], variant["description"], variant["hashtags"], "",
                        caption_words=words, passthrough=bool(item.get("passthrough")))
            clip.render_seconds = render_seconds
            clip.source_route = source_route
            ledger.record_clip(clip)
            output.append(clip)
    return output


def produce_ready(config, *, home=None, scout=None, campaign_clips=None, target_stock=20):
    home = clip_home(home)
    library_dir = home / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(home)
    plugins = config.get("plugins", {})
    if scout is None:
        try:
            scout_spec = plugins.get("scout", "scripts.public_discover.PublicDiscoverScout")
            if scout_spec == "scripts.scout.LocalCampaignScout":
                scout_spec = "scripts.public_discover.PublicDiscoverScout"
            scout = load_plugin(scout_spec, config={**config, "clip_home": str(home)})
        except (ImportError, AttributeError, ValueError) as exc:
            ledger.event("plugin_unavailable", {"plugin": "scout", "error": str(exc)})
            scout = None
    channels = config.get("channels", DEFAULT_CHANNELS)
    errors = []

    def report_error(kind, message, *, campaign_id=None):
        item = {"kind": kind, "message": str(message)}
        if campaign_id:
            item["campaign_id"] = campaign_id
        errors.append(item)
        ledger.event("producer_error", item)

    raw_campaigns = []
    if scout is None:
        report_error("scout_unavailable", "Campaign discovery plugin is unavailable")
    else:
        try:
            raw_campaigns = scout.list_campaigns()
        except Exception as exc:
            report_error("campaign_discovery_failed", f"{type(exc).__name__}: {exc}")
    campaigns = []
    for index, row in enumerate(raw_campaigns):
        try:
            campaign = _campaign(row)
            campaigns.append(campaign)
            ledger.record_campaign(campaign)
        except Exception as exc:
            report_error("campaign_contract_invalid", f"campaign {index}: {type(exc).__name__}: {exc}")
    eligibility_config = config
    joined_ids = getattr(scout, "joined_campaign_ids", None)
    if joined_ids is not None:
        eligibility_config = {**config, "approved_campaign_ids": sorted(
            set(config.get("approved_campaign_ids", [])) | set(joined_ids))}
    eligible = [campaign for campaign in campaigns if _campaign_eligible(campaign, eligibility_config, ledger)]
    history = config.get("approval_history", {})
    def approval_score(campaign_id):
        record = history.get(campaign_id, 0)
        return int(record.get("approved_count", 0)) if isinstance(record, dict) else int(record or 0)
    eligible.sort(key=lambda c: (c.cpm_usd, c.budget_left_usd or 0,
                                 approval_score(c.id),
                                 len(c.platforms)), reverse=True)
    ready_before = len(ledger.library_items("ready"))
    output = {"campaigns": len(eligible), "produced": 0, "qa_failures": 0, "ready": ready_before,
              "errors": errors, "error_count": 0, "failure_count": 0,
              "render_time_per_clip_seconds": {}, "source_routes": {}, "qa_rules_enforced": {}}
    if hasattr(scout, "join_suggestions"):
        try:
            output["join_suggestions"] = scout.join_suggestions()
        except Exception as exc:
            report_error("join_suggestions_failed", f"{type(exc).__name__}: {exc}")
            output["join_suggestions"] = []
    else:
        output["join_suggestions"] = []
    for campaign in eligible:
        checklist = parse_campaign_requirements(campaign.rules_text)
        ledger.save_campaign_checklist(campaign.id, checklist)
        output["qa_rules_enforced"][campaign.id] = checklist
        if campaign_clips is None and not _campaign_sources(campaign, home):
            report_error("campaign_sources_unavailable",
                         "No public detail, campaign-rule, or override source links found",
                         campaign_id=campaign.id)
            continue
        try:
            clips = list(campaign_clips[campaign.id]) if campaign_clips is not None else _prepare_clips(
                campaign, {**config, "channels": ["__library__"], "captions": False}, ledger, home)
        except Exception as exc:
            report_error("campaign_production_failed", f"{type(exc).__name__}: {exc}", campaign_id=campaign.id)
            continue
        if not clips and campaign_clips is None:
            report_error("campaign_no_clip_candidates",
                         "Source media produced no campaign-compliant clip candidates",
                         campaign_id=campaign.id)
        for original in clips:
            if getattr(original, "source_route", None):
                output["source_routes"].setdefault(campaign.id, original.source_route)
            output["render_time_per_clip_seconds"][original.id] = round(
                float(getattr(original, "render_seconds", 0)), 3
            )
            if original.channel_handle not in {"", "__library__"}:
                original.channel_handle = ""
            existing_item = ledger.library_item(original.id)
            if existing_item and existing_item["status"] == "posted":
                continue
            probe = _ffprobe(original.path) if Path(original.path).exists() else None
            failures = qa_clip(original, checklist, word_times=original.caption_words,
                               probe_fn=(lambda _: probe) if Path(original.path).exists() else None)
            ledger.record_clip(original)
            if failures:
                ledger.add_library_clip(original, checklist=checklist, status="failed", qa_failures=failures)
                output["qa_failures"] += 1
                continue
            source_path = Path(original.path)
            suffix = source_path.suffix or ".mp4"
            target = library_dir / f"{original.id}{suffix}"
            if source_path.resolve() != target.resolve():
                shutil.copy2(source_path, target)
            clip = Clip(**{**original.__dict__, "path": str(target), "channel_handle": ""})
            ledger.update_clip_path(clip)
            ledger.add_library_clip(clip, checklist=checklist, status="ready")
            output["produced"] += 1
            if len(ledger.library_items("ready")) >= target_stock:
                break
        if len(ledger.library_items("ready")) >= target_stock:
            break
    output["ready"] = len(ledger.library_items("ready"))
    for event in ledger.events():
        if event["kind"] != "campaign_source_selected":
            continue
        details = event["details"]
        output["source_routes"].setdefault(details["campaign_id"], details["route"])
    output["error_count"] = len(errors)
    output["failure_count"] = len(errors) + output["qa_failures"]
    if output["ready"] < target_stock:
        ledger.event("producer_stock_low", {"ready": output["ready"], "target": target_stock})
    return output


def run(config, *, home=None, scout=None, library=None, candidates=None, words=None,
        channels=None, clock=None, **_ignored):
    """Run Producer, with the small injected interface used by acceptance checks.

    Normal Glacier runs use the durable SQLite library in ``produce_ready``.
    The optional library/candidate arguments let callers supply another local
    library without giving Producer any YouTube or Whop write capability.
    """
    if library is None:
        return produce_ready(config, home=home, scout=scout,
                             target_stock=int(config.get("target_library_stock", 20)))

    scout = scout or FakeScout()
    campaign_rows = [_campaign(item) for item in scout.list_campaigns()]
    selected_channels = list(channels or config.get("channels", DEFAULT_CHANNELS))
    styles = {channel: channel_style(channel) for channel in selected_channels}
    timed_words = [dict(item) for item in (words or [])]
    active = styles[selected_channels[0]]["accent_color"] if selected_channels else "&H0000D7FF"
    for row in timed_words:
        row.setdefault("active_color", active)
        row.setdefault("highlight_color", active)

    ready, failures = [], []
    candidate_rows = list(candidates or [])
    for candidate in candidate_rows:
        campaign = next((item for item in campaign_rows if item.id == candidate.campaign_id), None)
        if campaign is None:
            failures.append("campaign requirements were not reviewed")
            continue
        checklist = parse_campaign_requirements(campaign.rules_text)
        caption_words = timed_words or candidate.caption_words
        issues = qa_clip(candidate, checklist, word_times=caption_words)
        if issues:
            failures.extend(issues)
            continue
        library.add_ready(candidate)
        ready.append(candidate)
    return {"campaigns": len(campaign_rows), "produced": len(ready), "ready": ready,
            "qa_failures": failures, "captions": timed_words, "channel_styles": styles}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Produce checked clips into the shared library")
    parser.add_argument("--config", type=Path, default=clip_home() / "config.json")
    parser.add_argument("--home", type=Path)
    parser.add_argument("--target-stock", type=int, default=20)
    args = parser.parse_args(argv)
    output = produce_ready(json.loads(args.config.read_text(encoding="utf-8")), home=args.home,
                           target_stock=args.target_stock)
    print(json.dumps(output, indent=2))
    return 1 if output["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
