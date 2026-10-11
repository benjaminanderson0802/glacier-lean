"""Hourly, deadline-aware dispatch from the ready library to linked channels."""
from __future__ import annotations

import argparse
import json
import os
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .cycle import DEFAULT_CHANNELS, FakeUploader, load_plugin
from .interfaces import Campaign, Clip
from .ledger import Ledger, clip_home
from .variants import channel_style
from .producer import qa_clip, _ffprobe


def _as_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _deadline(ledger, channel, now):
    last = ledger.last_post_at(channel)
    if last is None:
        return now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return last + timedelta(hours=6)


def _notify(config, message):
    urls = [url.strip() for url in os.environ.get("GLACIER_ALERT_URLS", "").split(",") if url.strip()]
    url = config.get("notification_url") or config.get("notifications", {}).get("url")
    if url:
        urls.extend(url if isinstance(url, list) else [url])
    urls = list(dict.fromkeys(urls))
    if not urls:
        return False
    try:
        import apprise
        notifier = apprise.Apprise()
        for target in urls:
            notifier.add(target)
        return bool(notifier.notify(title="Whop clipping deadline", body=message))
    except Exception:
        return False


def _send_deadline_alert(ledger, config, alert_fn, message, details):
    if alert_fn:
        alert_fn(message)
        sent = True
    else:
        sent = _notify(config, message)
    ledger.event("deadline_alert_sent" if sent else "deadline_alert_unavailable",
                 {**details, "message": message})


def _channel_assignment(ledger, channels, now, config):
    rows = []
    for channel in channels:
        settings = ledger.channel_config(channel)
        if settings["paused"] or ledger.is_paused(channel, None):
            continue
        last = ledger.last_post_at(channel)
        deadline = _deadline(ledger, channel, now)
        if last is None:
            due_at = now
        else:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            min_hours = min(6.0, max(2.0, float(config.get("min_spacing_hours", 2))))
            due_at = ledger.next_post_at(channel) or (last + timedelta(hours=min_hours))
            due_at = max(due_at, last + timedelta(hours=min_hours))
        if due_at <= now or deadline <= now + timedelta(hours=1):
            rows.append((deadline, last or datetime.min.replace(tzinfo=timezone.utc), channel, settings, due_at))
    return sorted(rows, key=lambda row: (row[0], row[1], row[2]))


def _channel_variant(clip, campaign, settings, home, checklist=None):
    style = channel_style(clip.channel_handle)
    from dataclasses import replace
    path = clip.path
    checklist = checklist or {}
    key_words = [campaign.name, *re.findall(r"[\w'-]+", campaign.name),
                 *re.findall(r"\b\d+(?:\.\d+)?\b", campaign.rules_text)]
    for value in [*checklist.get("mentions", []), *checklist.get("required_tags", [])]:
        key_words.extend(Path(str(value).replace("#", "").replace("@", "")).name.split())
    if not clip.passthrough and clip.caption_words:
        from .clipper import render_clip
        target = home / "media" / "channel-variants" / f"{clip.id}-{style['index']}.mp4"
        if not target.exists():
            render_clip(Path(clip.path), target, start_s=0, end_s=clip.end_s - clip.start_s,
                        caption_words=clip.caption_words,
                        caption_style={"caption": settings.get("caption_style") or style["caption"],
                                       "base_color": style["base_color"],
                                       "accent_color": style["accent_color"],
                                       "key_words": key_words if campaign else []})
        path = str(target)
    title = clip.title
    template = settings.get("title_template") or style["title"]
    hook = " ".join(clip.description.split()[:8])
    try:
        title = template.format(campaign=campaign.name if campaign else clip.campaign_id, hook=hook)[:100]
    except (KeyError, ValueError):
        pass
    return replace(clip, path=path, title=title)


def distribute_ready(config, *, home=None, uploader=None, now_fn=lambda: datetime.now(timezone.utc),
                     rng=None, sleep_fn=lambda _: None, alert_fn=None, dry_run=False, submitter=None):
    home = clip_home(home)
    ledger = Ledger(home)
    if not dry_run and not config.get("live", False):
        raise RuntimeError("live run refused: set live=true in the private config")
    if uploader is None:
        spec = config.get("plugins", {}).get("uploader", "youtube_upload.YouTubeUploader")
        try:
            uploader = load_plugin(spec, config=config)
        except (ImportError, AttributeError, ValueError) as exc:
            if not dry_run:
                raise
            uploader = FakeUploader()
            ledger.event("plugin_unavailable", {"plugin": "uploader", "error": str(exc)})
    if submitter is None:
        spec = config.get("plugins", {}).get("submitter", "scripts.submitter.ManualQueueSubmitter")
        submitter = load_plugin(spec, config={**config, "clip_home": str(home)})
    channels = config.get("channels", DEFAULT_CHANNELS)
    for channel, settings in config.get("channel_settings", {}).items():
        if channel in channels:
            ledger.set_channel_config(channel, caption=settings.get("caption_style", ""),
                                      title_template=settings.get("title_template", ""),
                                      paused=bool(settings.get("paused", False)),
                                      paused_reason=settings.get("paused_reason", ""))
    cap = min(6, max(0, int(config.get("daily_channel_cap", 6))))
    global_cap = min(100, max(0, int(config.get("global_daily_cap", 100))))
    min_spacing = timedelta(hours=min(6.0, max(2.0, float(config.get("min_spacing_hours", 2)))))
    max_spacing = timedelta(hours=min(6.0, max(min_spacing.total_seconds() / 3600,
                                               float(config.get("max_spacing_hours", 6)))))
    jitter_minutes = max(0, int(config.get("posting_jitter_minutes", 45)))
    rng = rng or random.Random()
    now = now_fn()
    ready = ledger.library_items("ready")
    available = _channel_assignment(ledger, channels, now, config)
    output = {"ready": len(ready), "uploads": 0, "skipped": 0, "deadline_at_risk": []}
    used_channels = set()
    for deadline, last, channel, settings, due_at in available:
        if channel in used_channels:
            continue
        if ledger.posts_today(channel, now.date().isoformat()) >= cap or ledger.global_posts_today(now.date().isoformat()) >= global_cap:
            if deadline <= now + timedelta(hours=1):
                msg = f"deadline at risk for {channel}: upload cap reached before {deadline.isoformat()}"
                ledger.event("deadline at risk", {"channel": channel, "deadline": deadline.isoformat(), "reason": "upload cap reached"})
                output["deadline_at_risk"].append(channel)
                _send_deadline_alert(ledger, config, alert_fn, msg, {"channel": channel, "deadline": deadline.isoformat()})
            output["skipped"] += 1
            continue
        candidates = []
        for item in ready:
            if item["clip_id"] in {row["clip_id"] for row in ledger.library_items("posted")}:
                continue
            clip_data = item["clip"]
            if clip_data.get("channel_handle") and clip_data["channel_handle"] != channel:
                continue
            clip = Clip(**{key: val for key, val in clip_data.items() if key in Clip.__dataclass_fields__})
            if ledger.is_paused(channel, clip.campaign_id):
                continue
            if ledger.any_segment_overlap(clip.source_id, clip.start_s, clip.end_s,
                                          except_clip_id=clip.id):
                continue
            candidates.append((ledger.campaign_channel_count(clip.campaign_id),
                               ledger.campaign_posts(channel, clip.campaign_id),
                               item["created_at"], item, clip))
        candidate = min(candidates, key=lambda row: (row[0], row[1], row[2], row[3]["clip_id"]))[3:] if candidates else None
        if not candidate:
            if deadline <= now + timedelta(hours=1):
                msg = f"deadline at risk for {channel}: no ready clips before {deadline.isoformat()}"
                ledger.event("deadline at risk", {"channel": channel, "deadline": deadline.isoformat(), "reason": "library empty"})
                output["deadline_at_risk"].append(channel)
                _send_deadline_alert(ledger, config, alert_fn, msg, {"channel": channel, "deadline": deadline.isoformat()})
            continue
        item, clip = candidate
        if not ledger.reserve_library_clip(clip.id, channel):
            continue
        campaign_data = ledger.campaign(clip.campaign_id) or {"id": clip.campaign_id, "name": clip.campaign_id,
                                                               "url": "", "cpm_usd": 0, "budget_left_usd": None,
                                                               "platforms": ["youtube"], "rules_text": ""}
        campaign = Campaign(**{key: campaign_data[key] for key in Campaign.__dataclass_fields__ if key in campaign_data})
        existing_post = ledger.post_for_clip(clip.id)
        if existing_post:
            ledger.finish_library_clip(clip.id, "posted")
            try:
                submitter.submit(campaign, existing_post, dry_run=False)
            except Exception:
                ledger.queue_submission(clip, campaign.name, existing_post.url)
            ledger.event("duplicate_upload_prevented", {"clip_id": clip.id, "existing_url": existing_post.url})
            continue
        if ledger.submitted_or_posted(clip.id):
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("duplicate_upload_prevented", {"clip_id": clip.id, "reason": "existing submission record"})
            continue
        variant = _channel_variant(clip, campaign, settings, home, item["checklist"])
        variant.channel_handle = channel
        probe = _ffprobe(variant.path) if Path(variant.path).exists() else None
        failures = qa_clip(variant, item["checklist"], word_times=variant.caption_words,
                           probe_fn=(lambda _: probe) if Path(variant.path).exists() else None)
        if failures:
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distributor_qa_failed", {"clip_id": clip.id, "channel": channel, "reasons": failures})
            output["skipped"] += 1
            continue
        scheduled = now + timedelta(minutes=rng.randint(0, jitter_minutes))
        scheduled = max(scheduled, due_at)
        if last != datetime.min.replace(tzinfo=timezone.utc):
            scheduled = max(scheduled, last + min_spacing)
        if scheduled > deadline:
            scheduled = deadline
        if scheduled - now < timedelta(0) or scheduled > deadline:
            output["deadline_at_risk"].append(channel)
            ledger.event("deadline at risk", {"channel": channel, "deadline": deadline.isoformat(), "reason": "spacing exceeded deadline"})
            _send_deadline_alert(ledger, config, alert_fn,
                f"deadline at risk for {channel}: spacing exceeds the next posting window",
                {"channel": channel, "deadline": deadline.isoformat()})
            ledger.finish_library_clip(clip.id, "ready")
            continue
        wait = (scheduled - now).total_seconds()
        if wait > 0:
            sleep_fn(wait)
        if dry_run:
            ledger.event("distribution_planned", {"clip_id": clip.id, "channel": channel,
                                                    "scheduled_at": scheduled.isoformat()})
            ledger.finish_library_clip(clip.id, "ready")
            output["skipped"] += 1
            continue
        try:
            post = uploader.upload(variant, dry_run=False)
        except Exception as exc:
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distribution_failed", {"clip_id": clip.id, "channel": channel, "error": str(exc)})
            output["skipped"] += 1
            continue
        if post.clip_id != clip.id or post.channel_handle != channel:
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distribution_response_mismatch", {"clip_id": clip.id, "channel": channel,
                "returned_clip_id": post.clip_id, "returned_channel": post.channel_handle})
            output["skipped"] += 1
            continue
        ledger.record_post(post)
        ledger.finish_library_clip(clip.id, "posted")
        posted_at = _as_datetime(post.posted_at) or scheduled
        randomized_window = max(timedelta(0), max_spacing - timedelta(hours=1) - min_spacing)
        extra_minutes = int(randomized_window.total_seconds() // 60)
        next_post = posted_at + min_spacing + timedelta(minutes=rng.randint(0, extra_minutes))
        ledger.set_next_post_at(channel, next_post)
        if posted_at > deadline:
            msg = f"deadline at risk for {channel}: posted after {deadline.isoformat()}"
            ledger.event("deadline at risk", {"channel": channel, "deadline": deadline.isoformat(), "reason": "late upload"})
            _send_deadline_alert(ledger, config, alert_fn, msg,
                                 {"channel": channel, "deadline": deadline.isoformat()})
        try:
            submitter.submit(campaign, post, dry_run=False)
        except Exception as exc:
            ledger.event("submitter_failed", {"clip_id": clip.id, "error": str(exc), "fallback": "manual queue"})
            ledger.queue_submission(variant, campaign.name, post.url)
        output["uploads"] += 1
        used_channels.add(channel)
        ledger.event("library_clip_posted", {"clip_id": clip.id, "channel": channel, "url": post.url})
    return output


def status_report(config, *, home=None, now_fn=lambda: datetime.now(timezone.utc), alert_fn=None):
    home = clip_home(home)
    ledger = Ledger(home)
    now = now_fn()
    for channel, settings in config.get("channel_settings", {}).items():
        ledger.set_channel_config(channel, caption=settings.get("caption_style", ""),
                                  title_template=settings.get("title_template", ""),
                                  paused=bool(settings.get("paused", False)),
                                  paused_reason=settings.get("paused_reason", ""))
    channels = {}
    for channel in config.get("channels", DEFAULT_CHANNELS):
        settings = ledger.channel_config(channel)
        deadline = _deadline(ledger, channel, now)
        last = ledger.last_post_at(channel)
        paused_reason = ledger.channel_pause_reason(channel)
        row = {"last_post": last.isoformat() if last else None,
               "next_deadline": deadline.isoformat(),
               "paused_reason": paused_reason or None,
               "paused": bool(paused_reason)}
        channels[channel] = row
        if not settings["paused"] and deadline <= now:
            msg = f"deadline at risk for {channel}: due {deadline.isoformat()}"
            ledger.event("deadline at risk", {"channel": channel, "deadline": deadline.isoformat(), "reason": "deadline reached"},
                         idempotency_key=f"deadline-risk:{channel}:{deadline.isoformat()}")
            _send_deadline_alert(ledger, config, alert_fn, msg, {"channel": channel, "deadline": deadline.isoformat()})
    waiting = ledger.submit_queue()
    campaigns = {}
    for item in ledger.library_items("ready"):
        campaigns[item["campaign_id"]] = campaigns.get(item["campaign_id"], 0) + 1
    failures = [event["details"] for event in ledger.events() if event["kind"] == "producer_qa_failed"]
    return {"channels": channels, "library_stock_by_campaign": campaigns,
            "producer_qa_failures": failures, "waiting_for_whop": len(waiting),
            "paused_channels": [channel for channel, data in channels.items() if data["paused"]]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Distribute ready clips to channels; Whop submission stays manual")
    parser.add_argument("--config", type=Path, default=clip_home() / "config.json")
    parser.add_argument("--home", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--live", action="store_true", help="upload only when private config also has live=true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.status:
        report = status_report(config, home=args.home)
        print(f"{report['waiting_for_whop']} clips waiting for you to submit on Whop")
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(distribute_ready(config, home=args.home,
                                          dry_run=(not args.live or args.dry_run)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
