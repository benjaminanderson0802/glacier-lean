"""Hourly, deadline-aware dispatch from the ready library to linked channels."""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .cycle import DEFAULT_CHANNELS, FakeUploader, _campaign, load_plugin
from .interfaces import Campaign, Clip
from .campaigns import load_campaign_registry
from .ledger import Ledger, clip_home, quota_day, exclusive_library_run
from .variants import (brand_spelling, campaign_brand, make_public_title, normalize_brand,
                       normalize_caption_words, required_mentions, required_tags, title_hook, channel_style)
from .producer import qa_clip, _ffprobe
from .policy import limits
from .quality import evaluate_quality, feedback_summary, record_review, render_review


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
            policy = limits(config)
            min_gap = timedelta(minutes=policy["min_gap_minutes"])
            due_at = ledger.next_post_at(channel) or (last + timedelta(minutes=policy["interval_minutes"]))
            due_at = max(due_at, last + min_gap)
        if due_at <= now or deadline <= now + timedelta(hours=1):
            rows.append((deadline, last or datetime.min.replace(tzinfo=timezone.utc), channel, settings, due_at))
    return sorted(rows, key=lambda row: (row[0], row[1], row[2]))


def _channel_variant(clip, campaign, settings, home, checklist=None):
    style = channel_style(clip.channel_handle)
    from dataclasses import replace
    path = clip.path
    checklist = checklist or {}
    brand = campaign_brand(campaign.name) if campaign else ""
    public_brand = brand_spelling(campaign.rules_text, brand) if campaign else brand
    rules_text = campaign.rules_text if campaign else ""
    key_words = [brand, *re.findall(r"[\w'-]+", brand),
                 *re.findall(r"\b\d+(?:\.\d+)?\b", rules_text)]
    for value in [*checklist.get("mentions", []), *checklist.get("required_tags", [])]:
        key_words.extend(Path(str(value).replace("#", "").replace("@", "")).name.split())
    if not clip.passthrough and clip.caption_words:
        from .clipper import render_clip
        target = home / "media" / "channel-variants" / f"{clip.id}-{style['index']}.mp4"
        # Re-render from the neutral base so changed text/style cannot reuse stale captions.
        if clip.caption_words:
            caption_words = normalize_caption_words(clip.caption_words, rules_text, brand)
            render_clip(Path(clip.base_path or clip.path), target, start_s=0, end_s=clip.end_s - clip.start_s,
                        caption_words=caption_words,
                        mode="center_crop",
                        caption_style={"caption": settings.get("caption_style") or style["caption"],
                                       "base_color": style["base_color"],
                                       "accent_color": style["accent_color"],
                                       "key_words": key_words if campaign else []})
        path = str(target)
    title = clip.title
    if campaign:
        description_lines = [line.strip() for line in clip.description.splitlines() if line.strip()]
        transcript = next((line for line in description_lines
                           if line.startswith(brand + ":")), "")
        hook = transcript.partition(":")[2].strip() or (description_lines[-1] if description_lines else clip.title)
        hook = title_hook(hook)
        hook = normalize_brand(hook, rules_text, brand)
        template = settings.get("title_template") or style["title"]
        title = make_public_title(hook, public_brand,
                                  [*required_mentions(rules_text), *required_tags(rules_text)],
                                  template=template)
        normalized_words = normalize_caption_words(clip.caption_words, rules_text, brand)
    else:
        normalized_words = clip.caption_words
    return replace(clip, path=path, base_path=clip.base_path or clip.path, title=title, caption_words=normalized_words)


@exclusive_library_run
def distribute_ready(config, *, home=None, uploader=None, now_fn=lambda: datetime.now(timezone.utc),
                     rng=None, sleep_fn=time.sleep, alert_fn=None, dry_run=False, submitter=None):
    home = clip_home(home)
    ledger = Ledger(home)
    if (home / "HOLD").exists():
        ledger.event("distribution_held", {"reason": "HOLD file exists"})
        return {"held": True, "uploads": 0, "skipped": 0, "ready": len(ledger.library_items()), "deadline_at_risk": []}
    if not dry_run and not config.get("live", False):
        raise RuntimeError("live run refused: set live=true in the private config")
    if uploader is None:
        spec = config.get("plugins", {}).get("uploader", "youtube_upload.YouTubeUploader")
        try:
            uploader = load_plugin(spec, config={**config, "clip_home": str(home)})
        except (ImportError, AttributeError, ValueError) as exc:
            if not dry_run:
                raise
            uploader = FakeUploader()
            ledger.event("plugin_unavailable", {"plugin": "uploader", "error": str(exc)})
    from .submitter import ManualQueueSubmitter
    if submitter is not None and not isinstance(submitter, ManualQueueSubmitter):
        ledger.event("non_manual_submitter_ignored", {"type": type(submitter).__name__})
    # Content Rewards has no approved automated integration. Always use the
    # local queue, even if a third-party submitter was supplied in config.
    submitter = ManualQueueSubmitter(config={**config, "clip_home": str(home)}, home=home)
    channels = config.get("channels", DEFAULT_CHANNELS)
    for channel, settings in config.get("channel_settings", {}).items():
        if channel in channels:
            ledger.set_channel_config(channel, caption=settings.get("caption_style", ""),
                                      title_template=settings.get("title_template", ""),
                                      paused=bool(settings.get("paused", False)),
                                      paused_reason=settings.get("paused_reason", ""))
    policy = limits(config)
    cap = policy["per_channel_daily"]
    global_cap = min(policy["daily_target"], policy["upload_cap"])
    min_spacing = timedelta(minutes=policy["min_gap_minutes"])
    max_spacing = timedelta(hours=min(6.0, max(min_spacing.total_seconds() / 3600,
                                               float(config.get("max_spacing_hours", 6)))))
    jitter_minutes = max(0, int(config.get("posting_jitter_minutes", 0)))
    rng = rng or random.Random()
    now = now_fn()
    ready = ledger.library_items("ready")
    available = _channel_assignment(ledger, channels, now, config)
    output = {"ready": len(ready), "uploads": 0, "skipped": 0, "deadline_at_risk": [],
              "paused_channels": [], "owner_actions": {}}
    used_channels = set()
    for deadline, last, channel, settings, due_at in available:
        if channel in used_channels:
            continue
        day = quota_day(now).isoformat()
        if ledger.upload_quota_remaining(now_fn(), cap=policy["upload_cap"]) == 0:
            output["quota_stopped"] = True
            ledger.event("distribution_quota_stopped", {"day": day, "cap": policy["upload_cap"]}, f"distribution-quota:{day}")
            break
        if (home / "HOLD").exists():
            output["held"] = True
            break
        if ledger.posts_today(channel, day) >= cap or ledger.global_posts_today(day) >= global_cap:
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
            if item.get("checklist", {}).get("draft_preapproval"):
                output["owner_actions"].setdefault(clip_data["campaign_id"], []).extend(
                    item.get("checklist", {}).get("owner_actions", [{
                        "requirement": "draft_preapproval", "reason": "draft must be approved before posting"}]))
                continue
            if clip_data.get("channel_handle") and clip_data["channel_handle"] != channel:
                continue
            clip = Clip(**{key: val for key, val in clip_data.items() if key in Clip.__dataclass_fields__})
            if ledger.is_paused(channel, clip.campaign_id):
                continue
            if any(other["source_id"] == clip.source_id and min(clip.end_s, other["end_s"]) >
                   max(clip.start_s, other["start_s"]) for other in ledger.quality_reference_clips(except_clip_id=clip.id)):
                ledger.finish_library_clip(clip.id, "failed")
                record_review(ledger, clip, {"score": 0, "reasons": ["source segment overlap across channels"]}, "rejected")
                continue
            candidates.append((ledger.campaign_channel_count(clip.campaign_id),
                               ledger.campaign_posts(channel, clip.campaign_id),
                               item["created_at"], item, clip))
        candidate = min(candidates, key=lambda row: (-row[4].quality.get("score", 0), row[0], row[1], row[2], row[3]["clip_id"]))[3:] if candidates else None
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
        clip.channel_handle = channel
        variant = clip
        try:
            variant = _channel_variant(clip, campaign, settings, home, item["checklist"])
            result = evaluate_quality(variant, item["checklist"], config, ledger)
            result["reasons"].extend(qa_clip(variant, item["checklist"], word_times=variant.caption_words))
        except Exception as exc:
            result = {"score": 0, "reasons": [f"variant quality check failed: {exc}"], "passed": False}
        failures = result["reasons"]
        result["passed"] = not failures
        variant.quality = result
        if failures:
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distributor_qa_failed", {"clip_id": clip.id, "channel": channel, "reasons": failures})
            record_review(ledger, variant, result, "rejected")
            output["skipped"] += 1
            continue
        scheduled = now + timedelta(minutes=rng.randint(0, jitter_minutes))
        scheduled = max(scheduled, due_at)
        if last != datetime.min.replace(tzinfo=timezone.utc):
            scheduled = max(scheduled, last + min_spacing)
        # A missed deadline never permits violating the minimum gap.
        if scheduled - now < timedelta(0) or scheduled > deadline and now < deadline:
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
        if (home / "HOLD").exists():
            ledger.finish_library_clip(clip.id, "ready")
            output["held"] = True
            break
        try:
            post = uploader.upload(variant, dry_run=False)
        except Exception as exc:
            if ledger.upload_quota_remaining(now_fn(), cap=policy["upload_cap"]) == 0:
                ledger.finish_library_clip(clip.id, "ready")
                output["quota_stopped"] = True
                break
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distribution_failed", {"clip_id": clip.id, "channel": channel, "error": str(exc)})
            if re.search(r"terms|strike|suspend|terminat|flagged|\b403\b", str(exc), re.I):
                ledger.pause(channel, clip.campaign_id, str(exc))
                output["paused_channels"].append(channel)
            output["skipped"] += 1
            continue
        if post.clip_id != clip.id or post.channel_handle != channel:
            ledger.finish_library_clip(clip.id, "failed")
            ledger.event("distribution_response_mismatch", {"clip_id": clip.id, "channel": channel,
                "returned_clip_id": post.clip_id, "returned_channel": post.channel_handle})
            output["skipped"] += 1
            continue
        ledger.record_post(post)
        ledger.update_clip_path(variant)
        ledger.finish_library_clip(clip.id, "posted")
        record_review(ledger, variant, result, "posted")
        posted_at = _as_datetime(post.posted_at) or scheduled
        next_post = posted_at + timedelta(minutes=policy["interval_minutes"])
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


def _run_injected_library(config, *, library, uploader, submitter, campaigns, clock,
                          simulation_hours=0, dry_run=False):
    """Dispatch through the documented library protocol used by local adapters."""
    clips = list(library.ready_clips())
    channels = list(config.get("channels") or
                    dict.fromkeys(clip.channel_handle for clip in clips if clip.channel_handle) or
                    DEFAULT_CHANNELS)
    policy = limits(config)
    cap = policy["per_channel_daily"]
    global_cap = min(policy["daily_target"], policy["upload_cap"])
    interval = timedelta(minutes=policy["interval_minutes"])
    # The owner requires a deadline no later than six hours after a post.
    max_spacing = timedelta(hours=min(6, max(2, float(config.get("max_spacing_hours", 6)))))
    campaign_by_id = {item.id: item for item in (_campaign(row) for row in (campaigns or []))}
    if not campaign_by_id:
        campaign_by_id = {item.id: item for item in (_campaign(row) for row in config.get("campaigns", []))}
    output = {"posts": [], "uploads": 0, "skipped": 0, "deadline_at_risk": [],
              "paused_channels": [], "pauses": []}
    live = bool(config.get("live", False)) and not dry_run
    if not live or (clip_home(config.get("clip_home")) / "HOLD").exists():
        return output

    hours = max(1, int(simulation_hours or 1))
    initial_clock = getattr(clock, "current", None) if clock is not None else None
    last_by_channel = {}
    counts_by_day = {}
    global_counts_by_day = {}
    assigned = set()
    for offset in range(hours):
        now = clock.now() if clock is not None else datetime.now(timezone.utc) + timedelta(hours=offset)
        for channel in channels:
            existing_pause = next((row for row in getattr(library, "pauses", set())
                                   if row[0] == channel and row[1] in (None, "")), None)
            if existing_pause:
                if channel not in output["paused_channels"]:
                    output["paused_channels"].append(channel)
                continue
            previous = last_by_channel.get(channel)
            if previous is not None and now - previous < interval:
                continue
            day = quota_day(now).isoformat()
            if counts_by_day.get((channel, day), 0) >= cap:
                continue
            if global_counts_by_day.get(day, 0) >= global_cap:
                continue
            candidate = None
            for clip in clips:
                if clip.id in assigned:
                    continue
                if clip.channel_handle and clip.channel_handle != channel:
                    continue
                if any(other.source_id == clip.source_id and
                       min(other.end_s, clip.end_s) > max(other.start_s, clip.start_s)
                       for other in clips if other.id != clip.id and other.id in assigned):
                    continue
                if any(row[0] == channel and row[1] in (None, "", clip.campaign_id)
                       for row in getattr(library, "pauses", set())):
                    continue
                candidate = clip
                break
            deadline = previous + max_spacing if previous is not None else now
            if candidate is None:
                if channel not in output["deadline_at_risk"]:
                    output["deadline_at_risk"].append(channel)
                    library.alert("deadline_at_risk", {"channel": channel,
                                  "deadline": deadline.isoformat(), "reason": "ready library stock is low"})
                continue

            candidate.channel_handle = channel
            campaign = campaign_by_id.get(candidate.campaign_id)
            if campaign is None:
                campaign = Campaign(candidate.campaign_id, candidate.campaign_id, "", 0, None,
                                    ["youtube_shorts"], "")
            try:
                post = uploader.upload(candidate, dry_run=False)
            except Exception as exc:
                reason = str(exc)
                if re.search(r"terms|strike|suspend|terminate|flagged|403", reason, re.I):
                    library.pause(channel, candidate.campaign_id, reason)
                    output["pauses"].append((channel, candidate.campaign_id, reason))
                    output["paused_channels"].append(channel)
                library.alert("distribution_failed", {"channel": channel, "clip_id": candidate.id,
                              "reason": reason})
                output["skipped"] += 1
                continue
            if post.channel_handle != channel or post.clip_id != candidate.id:
                library.alert("distribution_response_mismatch", {"channel": channel,
                              "clip_id": candidate.id})
                output["skipped"] += 1
                continue
            assigned.add(candidate.id)
            output["posts"].append(post)
            output["uploads"] += 1
            last_by_channel[channel] = _as_datetime(post.posted_at) or now
            counts_by_day[(channel, day)] = counts_by_day.get((channel, day), 0) + 1
            global_counts_by_day[day] = global_counts_by_day.get(day, 0) + 1
            item = {"campaign": campaign.name, "campaign_id": campaign.id, "channel": channel,
                    "url": post.url, "required_caption": candidate.description,
                    "required_tags": list(candidate.hashtags)}
            library.enqueue_submission(item)
        if clock is not None and simulation_hours and hasattr(clock, "advance"):
            clock.advance(timedelta(hours=1))
    # A simulation owns its elapsed time. Restore an injected test clock so
    # callers can compare simulated timestamps to the scenario's start date.
    if initial_clock is not None:
        clock.current = initial_clock
    return output


def run(config, *, home=None, library=None, uploader=None, submitter=None, campaigns=None,
        clock=None, simulation_hours=0, dry_run=None, **kwargs):
    """Run one hourly Distributor tick or a clock-driven acceptance simulation."""
    dry_run = (not bool(config.get("live", False))) if dry_run is None else bool(dry_run)
    if library is not None and not isinstance(library, Ledger):
        simulation_hours = simulation_hours or int(config.get("simulation_hours", 0))
        return _run_injected_library({**config, "clip_home": str(clip_home(home))}, library=library, uploader=uploader or FakeUploader(),
                                     submitter=submitter, campaigns=campaigns, clock=clock,
                                     simulation_hours=simulation_hours, dry_run=dry_run)
    now_fn = clock.now if clock is not None else kwargs.pop("now_fn", lambda: datetime.now(timezone.utc))
    return distribute_ready(config, home=home, uploader=uploader, submitter=submitter,
                            now_fn=now_fn, dry_run=dry_run, **kwargs)


def status_report(config, *, home=None, now_fn=lambda: datetime.now(timezone.utc), alert_fn=None):
    home = clip_home(home)
    ledger = Ledger(home)
    feedback = feedback_summary(ledger)
    review_path = render_review(ledger)
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
    suggestions = []
    suggestion_error = None
    try:
        saved_suggestions = home / "join_suggestions.json"
        if saved_suggestions.exists():
            record = json.loads(saved_suggestions.read_text(encoding="utf-8"))
            updated_at = float(record.get("updated_at", 0))
            if time.time() - updated_at < 60 * 60:
                suggestions = record.get("campaigns", [])
            else:
                suggestion_error = "cached campaign suggestions are older than one hour"
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        suggestion_error = str(exc)
    owner_actions = {}
    campaign_rows = {item["id"]: item for item in ledger.campaigns()}
    campaigns_dir = Path(config.get("campaigns_dir", Path(__file__).resolve().parents[1] / "campaigns"))
    registry_root = Path(config.get("campaign_registry", campaigns_dir.parent))
    try:
        for row in load_campaign_registry(registry_root, home, campaigns_dir=campaigns_dir):
            campaign_rows.setdefault(row.id, row.__dict__)
    except (OSError, ValueError, TypeError):
        pass
    for campaign_id, campaign in campaign_rows.items():
        actions = [{"requirement": str(item), "reason": "campaign brief requires owner action"}
                   for item in campaign.get("owner_requirements", [])]
        checklist = campaign.get("checklist", {})
        if checklist:
            actions.extend(checklist.get("owner_actions", []))
        if campaign.get("requires_draft_preapproval") or checklist.get("draft_preapproval"):
            actions.append({"requirement": "draft_preapproval", "reason": "draft must be approved before posting"})
        if actions:
            owner_actions[campaign_id] = actions
    return {"channels": channels, "library_stock_by_campaign": campaigns,
            "held": (home / "HOLD").exists(), "whop_feedback": feedback,
            "review_sheet": str(review_path), "limits": limits(config),
            "upload_quota_remaining": ledger.upload_quota_remaining(now, cap=limits(config)["upload_cap"]),
            "producer_qa_failures": failures, "waiting_for_whop": len(waiting),
            "paused_channels": [channel for channel, data in channels.items() if data["paused"]],
            "join_suggestions": suggestions, "join_suggestions_error": suggestion_error,
            "owner_actions": owner_actions}


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
        if report.get("join_suggestions"):
            print("Join these campaigns (then paste each URL into joined_campaigns.txt):")
            for campaign in report["join_suggestions"]:
                print(f"- {campaign['name']}: ${campaign['cpm_usd']:.2f} CPM, "
                      f"${campaign['budget_left_usd'] or 0:.2f} remaining — {campaign['url']}")
        elif report.get("join_suggestions_error"):
            print(f"Campaign discovery unavailable: {report['join_suggestions_error']}")
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(distribute_ready(config, home=args.home,
                                          dry_run=(not args.live or args.dry_run)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
