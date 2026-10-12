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
from .campaigns import allocate_daily_campaign_targets, load_campaign_registry
from .interfaces import Campaign, Clip
from .ledger import Ledger, clip_home, exclusive_library_run
from .clipper import candidate_segments, make_clip, transcribe
from .sources import fetch_source
from .policy import limits
from .quality import evaluate_quality, feedback_summary, record_review, render_review
from .variants import (assign_segments, brand_spelling, campaign_brand, make_variant,
                       normalize_brand, normalize_caption_words, required_mentions, required_tags, channel_style)

DEFAULT_CAMPAIGNS_DIR = Path(__file__).resolve().parents[1] / "campaigns"


def parse_campaign_requirements(rules_text: str) -> dict:
    tags = required_tags(rules_text)
    disclosures = []
    mentions = required_mentions(rules_text)
    links = list(dict.fromkeys(re.findall(r"https?://[^\s,)]+", rules_text)))
    banned_rules = []
    banned_content = []
    rule_fragments = []
    for line in rules_text.splitlines():
        if re.search(r"\b(?:must|should|required|tag|include|use|mention|banned|on-video captions)\b", line, re.I):
            for part in re.split(r"[;:.]", line):
                fragment = part.strip()
                if len(re.findall(r"\b\w+\b", fragment)) >= 4:
                    rule_fragments.append(fragment)
        match = re.search(r"(?:disclosure|must say|caption must)\s*[:=]?\s*(.+)", line, re.I)
        if match and re.search(r"\bdisclosure\s*[:=]", line, re.I):
            disclosures.append(match.group(1).strip())
        if re.match(r"\s*(?:banned|no\b)\s*[:=]?", line, re.I):
            banned_rules.append(line.strip())
            body = re.sub(r"^\s*(?:banned|no\b)\s*[:=]?\s*", "", line, flags=re.I)
            if re.match(r"\s*no\b", line, re.I) and not re.search(r"editing", body, re.I):
                banned_content.extend(part.strip(" .;,\t") for part in re.split(r"[,;]|\bor\b", body, flags=re.I)
                                      if part.strip(" .;,\t"))
            clauses = [part.strip(" .;,") for part in re.split(r"[;\n]", body) if part.strip(" .;,")]
            for clause in clauses:
                # Extract the named subject of a restriction while retaining broad topic terms.
                named = re.search(r"\b(?:clips?\s+of|mention(?:ing)?|about)\s+([\w'-]+)", clause, re.I)
                if named and not re.search(r"\b(?:stock|ticker)\b", clause, re.I):
                    banned_content.append(named.group(1))
                for topic in ("stock", "ticker", "story boosting", "negativity", "mocking", "low-effort bait"):
                    if re.search(re.escape(topic), clause, re.I):
                        banned_content.append(topic)
    min_match = re.search(r"\bmin(?:imum)?(?:imum)?\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)", rules_text, re.I)
    max_match = re.search(r"\bmax(?:imum)?(?:imum)?\s*(?:length)?\s*[:=]?\s*(\d+(?:\.\d+)?)", rules_text, re.I)
    edits_match = re.search(r"allowed edits?\s*[:=]\s*([^\n]+)", rules_text, re.I)
    banned_match = re.search(r"banned content\s*[:=]\s*([^\n]+)", rules_text, re.I)
    if banned_match:
        banned_content.extend(part.strip() for part in re.split(r"[,;]", banned_match.group(1)) if part.strip())
    no_edit = bool(re.search(r"no editing|do not edit|don't edit|unedited|as[- ]is", rules_text, re.I))
    if re.search(r"no editing\s*[:=]\s*(?:false|no|0)", rules_text, re.I):
        no_edit = False
    owner_actions = []
    owner_patterns = (
        ("link_in_bio", r"link\s+in\s+(?:the\s+)?bio"),
        ("demographics_screenshots", r"demographic(?:s|al)?[^\n]*(?:screenshot|screen shot)|(?:screenshot|screen shot)[^\n]*demographic"),
        ("draft_preapproval", r"(?:draft|pre[- ]?approval|approve[^\n]*before[^\n]*(?:post|publish))"),
    )
    for requirement, pattern in owner_patterns:
        if re.search(pattern, rules_text, re.I):
            owner_actions.append({"requirement": requirement, "reason": "requires owner action"})
    draft_preapproval = any(row["requirement"] == "draft_preapproval" for row in owner_actions)
    return {"rules_text": rules_text, "required_tags": tags, "disclosures": list(dict.fromkeys(disclosures)), "mentions": mentions,
            "links": links, "min_length_s": float(min_match.group(1)) if min_match else 0.0,
            "max_length_s": float(max_match.group(1)) if max_match else 58.0,
            "allowed_edits": [part.strip() for part in re.split(r"[,;]", edits_match.group(1))] if edits_match else [],
            "banned_content": list(dict.fromkeys(banned_content)), "banned_rules": banned_rules,
            "rule_fragments": list(dict.fromkeys(rule_fragments)),
            "brand_spelling": brand_spelling(rules_text, ""),
            "required_mentions": required_mentions(rules_text),
            "no_edit": no_edit, "owner_actions": owner_actions,
            "draft_preapproval": draft_preapproval}


def _rules_require_brand(rules_text: str, brand: str) -> bool:
    return bool(brand and re.search(rf"\bmention(?:ing)?\b[^\n.;]*\b{re.escape(brand)}\b",
                                    rules_text or "", re.I))


def qa_clip(clip: Clip, checklist: dict, *, word_times=(), probe_fn=None) -> list[str]:
    failures = []
    if not Path(clip.path).is_file():
        failures.append("rendered clip file is missing")
    duration = clip.end_s - clip.start_s
    if duration < float(checklist.get("min_length_s", 0)) or duration > float(checklist.get("max_length_s", 58)):
        failures.append("length outside campaign limits")
    metadata = "\n".join([clip.title, clip.description, *clip.hashtags])
    public_casefold = metadata.casefold()
    campaign_name = str(checklist.get("campaign_name", "")).strip()
    public_brand = campaign_brand(campaign_name)
    campaign_url = str(checklist.get("campaign_url", "")).strip()
    if campaign_name and campaign_name.casefold() != public_brand.casefold() \
            and campaign_name.casefold() in public_casefold:
        failures.append("internal campaign name leaked into public metadata: " + campaign_name)
    if campaign_url and campaign_url.casefold() in public_casefold:
        failures.append("internal campaign URL leaked into public metadata: " + campaign_url)
    for fragment in checklist.get("rule_fragments", []):
        words = fragment.split()
        candidates = [fragment, *[" ".join(words[index:]) for index in range(1, len(words) - 3)]]
        leaked = next((candidate for candidate in candidates if candidate.casefold() in public_casefold), None)
        if leaked:
            failures.append("campaign rule text leaked into public metadata: " + leaked)
    missing = [tag for tag in checklist.get("required_tags", []) if tag.lower() not in metadata.lower()]
    if missing:
        failures.append("required tags missing from clip metadata: " + ", ".join(missing))
    for required in [*checklist.get("disclosures", []), *checklist.get("mentions", []), *checklist.get("links", [])]:
        if required.lower() not in metadata.lower():
            failures.append("campaign requirement missing from metadata: " + required)
    spoken = " ".join(str(word.get("word", "")) for word in word_times)
    transcript_line = ""
    if campaign_name:
        brand_prefix = campaign_brand(campaign_name) + ":"
        transcript_line = next((line.partition(":")[2] for line in clip.description.splitlines()
                                if line.strip().casefold().startswith(brand_prefix.casefold())), "")
    spoken = " ".join((spoken, transcript_line))
    ticker_banned = any(term.casefold() == "ticker" for term in checklist.get("banned_content", []))
    if ticker_banned:
        brand_token = brand_spelling(checklist.get("rules_text", ""), public_brand).upper()
        symbols = [symbol for symbol in re.findall(r"(?<!\w)[A-Z]{2,5}(?!\w)", spoken)
                   if symbol != brand_token]
        if symbols:
            source_rule = next((line for line in checklist.get("banned_rules", [])
                                if re.search(r"\bticker\b", line, re.I)), "ticker")
            failures.append(f'banned campaign rule: "{source_rule}" (matched ticker: {symbols[0]})')
    for banned in checklist.get("banned_content", []):
        if banned and re.search(rf"\b{re.escape(banned.strip())}\b", spoken, re.I):
            source_rule = next((line for line in checklist.get("banned_rules", [])
                                if banned.casefold() in line.casefold()), banned)
            failures.append(f'banned campaign rule: "{source_rule}" (matched: {banned})')
    for mention in checklist.get("required_mentions", []):
        if mention.casefold() not in metadata.casefold():
            failures.append("required campaign handle missing from public metadata: " + mention)
    required_brand = str(checklist.get("required_brand", "")).strip()
    if required_brand and required_brand.casefold() not in clip.title.casefold():
        failures.append("required brand missing from title: " + required_brand)
    exact_spelling = str(checklist.get("brand_spelling", "")).strip()
    spelling_brand = campaign_brand(campaign_name)
    if exact_spelling and spelling_brand:
        if normalize_brand(clip.title, checklist.get("rules_text", ""), spelling_brand) != clip.title:
            failures.append("brand spelling in title must be exactly: " + exact_spelling)
        for word in word_times:
            spoken_word = str(word.get("word", ""))
            if normalize_brand(spoken_word, checklist.get("rules_text", ""), spelling_brand) != spoken_word:
                failures.append("burned-in caption spelling must be exactly: " + exact_spelling)
                break
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
        try:
            media = probe_fn(clip.path)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError,
                json.JSONDecodeError) as exc:
            failures.append(f"media probe failed: {type(exc).__name__}: {exc}")
        else:
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
    override = home / "campaign_sources" / f"{campaign.id}.txt"
    if override.is_file():
        urls = []
        for line in override.read_text(encoding="utf-8").splitlines():
            value = line.split("#", 1)[0].strip()
            if value.startswith(("https://", "http://")):
                urls.append(value)
        if urls:
            return [{"url": url, "route": "campaign_override"} for url in dict.fromkeys(urls)]
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

    return []


def _iter_prepared_clips(campaign, config, ledger, home, *, plan_only=False):
    source_cfg = config.get("sources", {})
    checklist = parse_campaign_requirements(campaign.rules_text)
    recovered = []
    for row in ledger.campaign_clips(campaign.id):
        library_item = ledger.library_item(row["id"])
        if library_item and library_item["status"] in {"ready", "posted", "failed"}:
            continue
        if Path(row.get("path", "")).is_file():
            recovered.append(Clip(**row))
    if recovered:
            for clip in recovered:
                yield (clip, None, None) if plan_only else clip
            return
    for source_item in _campaign_sources(campaign, home):
        url = source_item.get("url") if isinstance(source_item, dict) else str(source_item)
        source_route = source_item.get("route", "public_detail_page") if isinstance(source_item, dict) else "public_detail_page"
        source_id = str(source_item.get("id")) if isinstance(source_item, dict) and source_item.get("id") else _source_id(campaign.id, url)
        source = fetch_source(url, source_id, cache_dir=home / "media" / "sources", ledger=ledger,
                              max_bytes=int(source_cfg.get("max_bytes", 2_000_000_000)),
                              timeout_s=int(source_cfg.get("timeout_s", 1800)),
                              max_source_gb=float(source_cfg.get("max_source_gb", config.get("max_source_gb", 40))))
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
            words = [{**word,
                      "start": max(0.0, float(word["start"])-float(item["start_s"])),
                      "end": min(float(item["end_s"])-float(item["start_s"]), float(word["end"])-float(item["start_s"]))}
                     for word in item.get("words", [])]
            words = normalize_caption_words(words, campaign.rules_text, campaign_brand(campaign.name))
            clip = Clip(digest, campaign.id, source_id, item["start_s"], item["end_s"], str(target),
                        variant["title"], variant["description"], variant["hashtags"], "",
                        caption_words=words, passthrough=bool(item.get("passthrough")))
            clip.source_route = source_route
            plan = (clip, source.path, item)
            yield plan if plan_only else _render_plan(plan, config, ledger)


def _render_plan(plan, config, ledger):
    clip, source, item = plan
    if source is not None:
        target = Path(clip.path)
        started = time.monotonic()
        if not target.exists():
            make_clip(source, target, item, requires_editing=not clip.passthrough,
                      caption_words=False, mode=config.get("video_layout", "blurred_background"))
            clip.render_seconds = time.monotonic() - started
        ledger.record_clip(clip)
    return clip


def _prepare_clips(campaign, config, ledger, home):
    """Compatibility list wrapper; Producer itself consumes the iterator."""
    return list(_iter_prepared_clips(campaign, config, ledger, home))


@exclusive_library_run
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
    registry_root = Path(config.get("campaign_registry", Path(__file__).resolve().parents[1]))
    default_campaigns_dir = registry_root / "campaigns" if "campaign_registry" in config else DEFAULT_CAMPAIGNS_DIR
    campaigns_dir = Path(config.get("campaigns_dir", default_campaigns_dir))
    try:
        raw_campaigns.extend(load_campaign_registry(registry_root, home, campaigns_dir=campaigns_dir))
    except Exception as exc:
        report_error("campaign_registry_failed", f"{type(exc).__name__}: {exc}")
    if scout is None:
        report_error("scout_unavailable", "Campaign discovery plugin is unavailable")
    else:
        try:
            discovered = scout.list_campaigns()
            known = {row.id if isinstance(row, Campaign) else str(row.get("id")) for row in raw_campaigns}
            raw_campaigns.extend(row for row in discovered if
                                (row.id if isinstance(row, Campaign) else str(row.get("id"))) not in known)
        except Exception as exc:
            report_error("campaign_discovery_failed", f"{type(exc).__name__}: {exc}")
    campaigns = []
    for index, row in enumerate(raw_campaigns):
        try:
            campaign = _campaign(row)
            rules_override = home / "campaign_rules" / f"{campaign.id}.txt"
            if rules_override.is_file():
                campaign.rules_text = rules_override.read_text(encoding="utf-8")
            campaigns.append(campaign)
            ledger.record_campaign(campaign)
        except Exception as exc:
            report_error("campaign_contract_invalid", f"campaign {index}: {type(exc).__name__}: {exc}")
    eligibility_config = config
    joined_ids = set(getattr(scout, "joined_campaign_ids", None) or [])
    if joined_ids:
        eligibility_config = {**config, "approved_campaign_ids": sorted(
            set(config.get("approved_campaign_ids", [])) | joined_ids)}
    eligible = []
    for campaign in campaigns:
        eligibility = campaign.eligible_for_new_youtube_shorts_channels
        allow_conditional = set(config.get("allow_conditional_campaign_ids", []))
        is_yes = eligibility is True or (isinstance(eligibility, str) and eligibility.strip().casefold() == "yes")
        is_conditional = isinstance(eligibility, str) and eligibility.strip().casefold() == "conditional"
        if eligibility is not None and not is_yes and not (is_conditional and campaign.id in allow_conditional):
            report_error("campaign_ineligible", f"campaign eligibility is {eligibility!r}",
                         campaign_id=campaign.id)
            continue
        if _campaign_eligible(campaign, eligibility_config, ledger):
            eligible.append(campaign)
    history = config.get("approval_history", {})
    def approval_score(campaign_id):
        record = history.get(campaign_id, 0)
        return int(record.get("approved_count", 0)) if isinstance(record, dict) else int(record or 0)
    eligible.sort(key=lambda c: (c.cpm_usd, c.budget_left_usd or 0,
                                 approval_score(c.id),
                                 len(c.platforms)), reverse=True)
    ready_before = len(ledger.library_items("ready"))
    daily_target = limits(config)["daily_target"]
    feedback = feedback_summary(ledger)
    capacities, source_plans = {}, {}
    if campaign_clips is None:
        from itertools import islice
        for campaign in eligible:
            source_plans[campaign.id] = []
            if _campaign_sources(campaign, home) and ledger.ready_today() < daily_target:
                try:
                    plans = _iter_prepared_clips(campaign, {**config, "channels": ["__library__"]}, ledger, home, plan_only=True)
                    for plan in islice(plans, daily_target):
                        clip = plan[0]
                        if not any(other[0].source_id == clip.source_id and min(other[0].end_s, clip.end_s) >
                                   max(other[0].start_s, clip.start_s) for other in source_plans[campaign.id]):
                            source_plans[campaign.id].append(plan)
                except Exception as exc:
                    report_error("campaign_production_failed", f"{type(exc).__name__}: {exc}", campaign_id=campaign.id)
            capacities[campaign.id] = ledger.campaign_ready_today(campaign.id) + len(source_plans[campaign.id])
    if campaign_clips is not None:
        for campaign_id, candidates in campaign_clips.items():
            if isinstance(candidates, (list, tuple)):
                distinct = []
                for candidate in candidates:
                    if not any(other.source_id == candidate.source_id and min(other.end_s, candidate.end_s) >
                               max(other.start_s, candidate.start_s) for other in distinct):
                        distinct.append(candidate)
                capacities[campaign_id] = ledger.campaign_ready_today(campaign_id) + len(distinct)
    campaign_targets = allocate_daily_campaign_targets(eligible, daily_target, capacities=capacities, feedback=feedback)
    output = {"campaigns": len(eligible), "produced": 0, "qa_failures": 0, "ready": ready_before,
              "errors": errors, "error_count": 0, "failure_count": 0,
              "render_time_per_clip_seconds": {}, "source_routes": {}, "qa_rules_enforced": {},
              "daily_target": daily_target, "daily_ready": ledger.ready_today(),
              "campaign_targets": campaign_targets,
              "whop_feedback": feedback, "distinct_moment_capacity": capacities,
              "owner_actions": {}}
    if hasattr(scout, "join_suggestions"):
        try:
            output["join_suggestions"] = scout.join_suggestions()
        except Exception as exc:
            report_error("join_suggestions_failed", f"{type(exc).__name__}: {exc}")
            output["join_suggestions"] = []
    else:
        output["join_suggestions"] = []
    for campaign in eligible:
        checklist = {**parse_campaign_requirements(campaign.rules_text),
                     "campaign_name": campaign.name, "campaign_url": campaign.url,
                     "required_brand": (campaign_brand(campaign.name)
                                        if _rules_require_brand(campaign.rules_text, campaign_brand(campaign.name)) else "")}
        if campaign.requires_draft_preapproval:
            checklist["draft_preapproval"] = True
            checklist["owner_actions"] = list(checklist["owner_actions"]) + [
                {"requirement": "draft_preapproval", "reason": "summary requires pre-approval"}]
        for requirement in campaign.owner_requirements:
            checklist["owner_actions"].append({"requirement": str(requirement), "reason": "campaign brief requires owner action"})
        ledger.save_campaign_checklist(campaign.id, checklist)
        output["qa_rules_enforced"][campaign.id] = checklist
        if checklist["owner_actions"]:
            output["owner_actions"][campaign.id] = checklist["owner_actions"]
        if campaign_clips is None and not _campaign_sources(campaign, home):
            report_error("campaign_sources_unavailable",
                         "No public detail, campaign-rule, or override source links found",
                         campaign_id=campaign.id)
            continue
        if ledger.campaign_ready_today(campaign.id) >= campaign_targets.get(campaign.id, 0):
            continue
        def rendered_plans():
            for plan in source_plans.get(campaign.id, []):
                try:
                    yield _render_plan(plan, config, ledger)
                except Exception as exc:
                    report_error("campaign_render_failed", f"{type(exc).__name__}: {exc}", campaign_id=campaign.id)
                    yield plan[0]  # The missing/broken media fails QA with a review entry.
        try:
            clips = iter(campaign_clips.get(campaign.id, [])) if campaign_clips is not None else rendered_plans()
        except Exception as exc:
            report_error("campaign_production_failed", f"{type(exc).__name__}: {exc}", campaign_id=campaign.id)
            continue
        if not clips and campaign_clips is None:
            report_error("campaign_no_clip_candidates",
                         "Source media produced no campaign-compliant clip candidates",
                         campaign_id=campaign.id)
        seen_moments = []
        for original in clips:
            if ledger.campaign_ready_today(campaign.id) >= campaign_targets.get(campaign.id, 1):
                break
            if any(other.source_id == original.source_id and min(other.end_s, original.end_s) >
                   max(other.start_s, original.start_s) for other in seen_moments):
                record_review(ledger, original, {"score": 0, "reasons": ["duplicate source moment"]}, "rejected")
                continue
            seen_moments.append(original)
            if getattr(original, "source_route", None):
                output["source_routes"].setdefault(campaign.id, original.source_route)
            output["render_time_per_clip_seconds"][original.id] = round(
                float(getattr(original, "render_seconds", 0)), 3
            )
            if original.channel_handle not in {"", "__library__"}:
                original.channel_handle = ""
            existing_item = ledger.library_item(original.id)
            if existing_item and existing_item["status"] in {"ready", "posted"}:
                continue
            from dataclasses import replace
            preview = original
            try:
                if not original.passthrough:
                    from .clipper import render_clip
                    base = original.base_path or original.path
                    target = home / "media" / "quality-previews" / f"{original.id}.mp4"
                    render_clip(Path(base), target, start_s=0, end_s=original.end_s-original.start_s,
                                caption_words=original.caption_words, mode="center_crop")
                    preview = replace(original, path=str(target), base_path=base)
                result = evaluate_quality(preview, checklist, config, ledger)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                result = {"passed": False, "score": 0, "signals": {}, "reasons": [f"preview render failed: {exc}"]}
            failures = qa_clip(preview, checklist, word_times=preview.caption_words)
            result["reasons"] = list(dict.fromkeys([*result["reasons"], *failures]))
            result["passed"] = not result["reasons"]
            failures = result["reasons"]
            original.quality = result
            ledger.record_clip(original)
            ledger.update_clip_path(original)
            if failures:
                ledger.add_library_clip(original, checklist=checklist, status="failed", qa_failures=failures)
                record_review(ledger, preview, result, "rejected")
                output["qa_failures"] += 1
                continue
            source_path = Path(preview.path)
            suffix = source_path.suffix or ".mp4"
            target = library_dir / f"{original.id}{suffix}"
            base_path = original.base_path or original.path
            if not original.passthrough:
                stored_base = library_dir / f"{original.id}-base.mp4"
                if Path(base_path).resolve() != stored_base.resolve():
                    shutil.copy2(base_path, stored_base)
                base_path = str(stored_base)
            if source_path.resolve() != target.resolve():
                shutil.copy2(source_path, target)
            clip = Clip(**{**original.__dict__, "path": str(target), "base_path": base_path, "channel_handle": ""})
            ledger.update_clip_path(clip)
            ledger.add_library_clip(clip, checklist=checklist, status="ready")
            output["produced"] += 1
            if ledger.ready_today() >= daily_target:
                break
        else:
            # Source stream exhausted: only real distinct moments can support an allocation.
            capacities[campaign.id] = ledger.campaign_ready_today(campaign.id)
            campaign_targets[campaign.id] = min(campaign_targets.get(campaign.id, 0), capacities[campaign.id])
        if ledger.ready_today() >= daily_target:
            break
    output["ready"] = len(ledger.library_items("ready"))
    output["daily_ready"] = ledger.ready_today()
    for event in ledger.events():
        if event["kind"] != "campaign_source_selected":
            continue
        details = event["details"]
        output["source_routes"].setdefault(details["campaign_id"], details["route"])
    output["error_count"] = len(errors)
    output["failure_count"] = len(errors) + output["qa_failures"]
    render_review(ledger)
    if output["daily_ready"] < daily_target:
        ledger.event("producer_stock_low", {"ready": output["ready"], "daily_ready": output["daily_ready"],
                                             "target": daily_target})
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
        checklist = {**parse_campaign_requirements(campaign.rules_text),
                     "campaign_name": campaign.name, "campaign_url": campaign.url,
                     "required_brand": (campaign_brand(campaign.name)
                                        if _rules_require_brand(campaign.rules_text, campaign_brand(campaign.name)) else "")}
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
