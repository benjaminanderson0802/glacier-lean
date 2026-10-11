"""Stable per-channel styling and overlap-safe campaign variants."""
from __future__ import annotations

import hashlib
import re


STYLES = (
    {"caption": "bold_center", "title": "A moment from {campaign}: {hook}"},
    {"caption": "clean_lower", "title": "The replay: {hook}"},
    {"caption": "highlight_words", "title": "Watch this {campaign} moment"},
    {"caption": "compact_top", "title": "{hook} | {campaign}"},
    {"caption": "outline_center", "title": "Quick cut: {hook}"},
    {"caption": "boxed_lower", "title": "One for the archive: {hook}"},
    {"caption": "two_line_center", "title": "The detail you missed: {hook}"},
    {"caption": "minimal_bottom", "title": "Replay notes: {hook}"},
    {"caption": "emphasis_pulse", "title": "In this clip: {hook}"},
    {"caption": "small_caps_top", "title": "Scene select: {hook}"},
)

CHANNEL_STYLE_INDEX = {
    "@frameandmomentdesk": 0, "@highlightdesknotes": 1, "@replaynotesdesk": 2,
    "@quickreplaydesk": 3, "@dailycutnotes": 4, "@clipcurrentdesk": 5,
    "@sceneselectnotes": 6, "@momentarchivedesk": 7, "@thecliproomnotes": 8,
    "@contextclipsdesk": 9,
}

CHANNEL_COLOR_PAIRS = (
    ("&H00FFFFFF", "&H0000D7FF"), ("&H00FFF4D6", "&H00FF7A00"),
    ("&H00FFFFFF", "&H00FF4DB8"), ("&H00E8FFFF", "&H00FFD000"),
    ("&H00FFFFFF", "&H0000E070"), ("&H00F5F5FF", "&H00FF5040"),
    ("&H00FFFFFF", "&H00D080FF"), ("&H00FFFDF0", "&H00FF6B6B"),
    ("&H00FFFFFF", "&H0000C8C8"), ("&H00F8F8F8", "&H00A0D000"),
)


def channel_style(channel: str):
    index = CHANNEL_STYLE_INDEX.get(channel.lower())
    if index is None:
        index = int(hashlib.sha256(channel.lower().encode("utf-8")).hexdigest()[:8], 16) % len(STYLES)
    base, accent = CHANNEL_COLOR_PAIRS[index]
    return {**STYLES[index], "base_color": base, "accent_color": accent, "index": index}


def required_tags(rules_text: str):
    tags = set(re.findall(r"(?<!\w)#[\w-]+", rules_text))
    patterns = (r"(?:required|include|must use|hashtag|tags?)\s*[:=]\s*([^\n.]+)",)
    for pattern in patterns:
        for match in re.finditer(pattern, rules_text, re.I):
            tags.update(re.findall(r"(?<!\w)#[\w-]+", match.group(1)))
    return sorted(tags, key=str.lower)


def required_disclosures(rules_text: str):
    disclosures = []
    for line in rules_text.splitlines():
        if re.search(r"disclosure|must say|caption must|include in (?:the )?(?:caption|description)", line, re.I):
            value = re.sub(r"^.*?(?:disclosure|must say|caption must|include in (?:the )?(?:caption|description))\s*[:=]?\s*", "", line, flags=re.I).strip()
            if value:
                disclosures.append(value)
    if re.search(r"\bad\b|paid partnership|sponsored", rules_text, re.I):
        if "#ad" not in {tag.lower() for tag in required_tags(rules_text)}:
            disclosures.append("#ad")
    return list(dict.fromkeys(disclosures))


def make_variant(campaign, segment, channel: str):
    text = re.sub(r"\s+", " ", segment.get("text", "")).strip()
    hook = " ".join(text.split()[:8]).strip(" .,!?:;") or campaign.name
    style = channel_style(channel)
    title = style["title"].format(campaign=campaign.name, hook=hook)[:100]
    hashtags = required_tags(campaign.rules_text)
    disclosure = required_disclosures(campaign.rules_text)
    desc_lines = [text, f"Campaign: {campaign.name}"]
    if campaign.url:
        desc_lines.append(campaign.url)
    desc_lines.extend(disclosure)
    if hashtags:
        desc_lines.append(" ".join(hashtags))
    return {"title": title, "description": "\n\n".join(dict.fromkeys(line for line in desc_lines if line)),
            "hashtags": hashtags, "channel_handle": channel, "caption_style": style["caption"]}


def _overlaps(a, b):
    overlap = max(0.0, min(a["end_s"], b["end_s"]) - max(a["start_s"], b["start_s"]))
    return overlap > 0


def assign_segments(segments, channels, ledger=None):
    """Return unique segment/channel pairs, excluding previously allocated overlaps."""
    if not channels:
        return []
    chosen = []
    for segment in sorted(segments, key=lambda item: item.get("score", 0), reverse=True):
        if segment.get("end_s", 0) <= segment.get("start_s", 0):
            continue
        if any(other["source_id"] == segment["source_id"] and _overlaps(other, segment) for other, _ in chosen):
            continue
        channel = ledger.existing_channel(segment["source_id"], segment["start_s"], segment["end_s"]) if ledger else None
        if channel is not None:
            if channel not in channels:
                continue
        else:
            if ledger and ledger.any_segment_overlap(segment["source_id"], segment["start_s"], segment["end_s"]):
                continue
            channel = channels[len(chosen) % len(channels)]
        chosen.append((segment, channel))
    return [{**segment, "channel_handle": channel} for segment, channel in chosen]
