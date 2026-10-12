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

INTERNAL_NAME_WORDS = {"clipping", "official", "campaign"}
TRAILING_HOOK_FRAGMENTS = {"a", "an", "and", "because", "but", "he", "it", "she", "that", "the", "they", "this", "to"}


def campaign_brand(name: str) -> str:
    words = [word for word in re.findall(r"[\w&'-]+", name or "")
             if word.casefold() not in INTERNAL_NAME_WORDS]
    return " ".join(words).strip()


def brand_spelling(rules_text: str, brand: str) -> str:
    match = re.search(r"\bspell\s+(?:the\s+)?([A-Z][A-Z0-9]{1,})\s+(?:correctly|in\s+caps|in\s+uppercase)",
                      rules_text or "", re.I)
    if match:
        return match.group(1).upper()
    # A clearly all-caps brand immediately attached to a spelling instruction is authoritative.
    match = re.search(r"\bspell\s+(?:the\s+)?([A-Z][A-Z0-9]{1,})\b", rules_text or "", re.I)
    return match.group(1).upper() if match and match.group(1).isupper() else brand


def normalize_brand(text: str, rules_text: str, brand: str) -> str:
    exact = brand_spelling(rules_text, brand)
    if not exact:
        return text
    if exact.casefold() == "boxabl":
        pattern = r"(?<![@#\w])(?:box\s*able|boxable|boxabl)\b"
        return re.sub(pattern, exact, text, flags=re.I)
    escaped = r"\s*".join(re.escape(part) for part in exact.split())
    return re.sub(rf"(?<![@#\w]){escaped}\b", exact, text, flags=re.I)


def normalize_caption_words(words, rules_text: str, brand: str):
    result = []
    values = list(words or [])
    exact = brand_spelling(rules_text, brand)
    index = 0
    while index < len(values):
        current = dict(values[index])
        value = str(current.get("word", ""))
        next_value = str(values[index + 1].get("word", "")) if index + 1 < len(values) else ""
        if exact.casefold() == "boxabl" and value.strip(" ,.!?:;").casefold() == "box" \
                and next_value.strip(" ,.!?:;").casefold() == "able":
            punctuation = value[-1] if value and value[-1] in ",.!?;:" else ""
            current["word"] = exact + punctuation
            current["end"] = values[index + 1].get("end", current.get("end"))
            result.append(current)
            index += 2
            continue
        current["word"] = normalize_brand(value, rules_text, brand)
        result.append(current)
        index += 1
    return result


def make_public_title(hook: str, brand: str, social_tags=(), template=None) -> str:
    suffix = "#shorts"
    all_tags = list(dict.fromkeys([*social_tags, suffix]))
    # Keep the platform tag and as many required social tags as fit.
    tags = [suffix]
    for tag in all_tags:
        if tag != suffix and len(" ".join([*tags[:-1], tag, suffix])) <= 35:
            tags.insert(-1, tag)
    tail = " ".join(tags)
    hook = hook.strip(" .,!?:;")
    try:
        core = template.format(campaign=brand, hook=hook) if template else hook
    except (KeyError, ValueError, AttributeError):
        core = hook
    core = core.strip(" .,!?:;")
    has_brand = bool(brand and re.search(rf"(?<!\w){re.escape(brand)}(?!\w)", core, re.I))
    if brand and not has_brand:
        core = f"{brand} {core}".strip()
    elif brand:
        seen = False

        def keep_first_brand(_match):
            nonlocal seen
            if seen:
                return ""
            seen = True
            return brand

        core = re.sub(rf"(?<!\w){re.escape(brand)}(?!\w)", keep_first_brand, core, flags=re.I)
    core = re.sub(r"\s+([:|—-])", r"\1", core)
    core = re.sub(r"\s{2,}", " ", core).strip()
    room = max(0, 100 - len(tail) - 1)
    core = core[:room].rsplit(" ", 1)[0] if len(core) > room else core
    core = core.rstrip(" ,.!?:;-|—")
    return f"{core} {tail}".strip()


def title_hook(text: str, limit=8) -> str:
    words = (text or "").split()[:limit]
    while words and words[-1].strip(".,!?;:").casefold() in TRAILING_HOOK_FRAGMENTS:
        words.pop()
    if len(words) > 1 and words[-2].strip(".,!?;:").casefold() in {"it", "he", "she", "they", "this", "that"}:
        words = words[:-2]
    return " ".join(words).strip(" .,!?:;")

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
    tags = set()
    for line in (rules_text or "").splitlines():
        if re.search(r"\b(?:required|tag|use|include|hashtag|tags?)\b", line, re.I):
            tags.update(re.findall(r"(?<!\w)#[\w-]+", line))
    return sorted(tags, key=str.lower)


def required_mentions(rules_text: str):
    mentions = set()
    for line in (rules_text or "").splitlines():
        if re.search(r"\b(?:required|tag|use|include|mention|mentions)\b", line, re.I):
            mentions.update(re.findall(r"(?<!\w)@[\w.-]+", line))
    return sorted(mentions, key=str.lower)


def required_disclosures(rules_text: str):
    disclosures = []
    for line in rules_text.splitlines():
        if re.search(r"\bdisclosure\s*[:=]", line, re.I):
            value = re.sub(r"^.*?\bdisclosure\s*[:=]\s*", "", line, flags=re.I).strip()
            if value:
                disclosures.append(value)
    if re.search(r"\bad\b|paid partnership|sponsored", rules_text, re.I):
        if "#ad" not in {tag.lower() for tag in required_tags(rules_text)}:
            disclosures.append("#ad")
    return list(dict.fromkeys(disclosures))


def make_variant(campaign, segment, channel: str):
    text = re.sub(r"\s+", " ", segment.get("text", "")).strip()
    brand = campaign_brand(campaign.name)
    public_brand = brand_spelling(campaign.rules_text, brand)
    text = normalize_brand(text, campaign.rules_text, brand)
    hook = title_hook(text) or brand
    style = channel_style(channel)
    hook = normalize_brand(hook, campaign.rules_text, brand)
    title = make_public_title(hook, public_brand,
                              [*required_mentions(campaign.rules_text), *required_tags(campaign.rules_text)],
                              template=style["title"])
    hashtags = [*required_mentions(campaign.rules_text), *required_tags(campaign.rules_text), "#shorts"]
    hashtags = list(dict.fromkeys(hashtags))
    disclosure = required_disclosures(campaign.rules_text)
    first_line = " ".join(hashtags)
    desc_lines = [first_line, f"{public_brand}: {text}", *disclosure]
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
