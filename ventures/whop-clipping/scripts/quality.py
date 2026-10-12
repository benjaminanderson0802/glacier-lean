"""Local media evidence, quality ranking, duplicate rejection and owner review.

Scores are transparent heuristics, not a claim of semantic understanding. Every
hard check must pass independently of the score. No network or model API is used.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from .ledger import quota_day


def _run(binary, args, *, binary_output=False):
    executable = shutil.which(binary)
    if not executable:
        raise RuntimeError(f"{binary} is required for quality evidence")
    return subprocess.run([executable, *args], check=True, capture_output=True,
                          text=not binary_output, timeout=180)


def _numbers(log, key):
    return [float(value) for value in re.findall(re.escape(key) + r"[:=]\s*(-?[\d.]+)", log)]


def _intervals(log, prefix, duration):
    intervals, start = [], None
    for key, value in re.findall(rf"{prefix}_(start|end)[:=]\s*([\d.]+)", log):
        if key == "start":
            start = float(value)
        elif start is not None:
            intervals.append((start, float(value)))
            start = None
    if start is not None:
        intervals.append((start, duration))
    return intervals


def _frames(path, *, fps=2, size="64:64", crop=""):
    filters = ",".join(part for part in (crop, f"fps={fps}", f"scale={size}", "format=gray") if part)
    data = _run("ffmpeg", ["-v", "error", "-i", str(path), "-vf", filters,
                           "-an", "-f", "rawvideo", "-threads", "1", "-"], binary_output=True).stdout
    width, height = map(int, size.split(":"))
    stride = width * height
    return [data[i:i + stride] for i in range(0, len(data) - stride + 1, stride)]


def _frame(path, at):
    result = _run("ffmpeg", ["-v", "error", "-ss", str(at), "-i", str(path), "-frames:v", "1",
                              "-vf", "scale=270:480,format=gray", "-f", "rawvideo", "-threads", "1", "-"], binary_output=True)
    if len(result.stdout) != 270 * 480:
        raise RuntimeError("caption comparison frame is missing")
    return result.stdout


def _difference(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a))


def _hash(frame):
    # Difference perceptual hash: 9x8 luminance, invariant to modest encoding changes.
    bits = [frame[y * 9 + x] > frame[y * 9 + x + 1] for y in range(8) for x in range(8)]
    return f"{sum(int(bit) << i for i, bit in enumerate(bits)):016x}"


def inspect_media(path):
    data = json.loads(_run("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    duration = float(data.get("format", {}).get("duration", video.get("duration", 0)))
    if not math.isfinite(duration) or duration <= 0 or duration > 600:
        raise ValueError("invalid or excessive clip duration")
    args = ["-hide_banner", "-nostats", "-i", str(path), "-vf",
            "blackdetect=d=2:pix_th=0.10,freezedetect=n=-50dB:d=2"]
    if audio:
        args += ["-af", "silencedetect=n=-40dB:d=0.05,ebur128=peak=true"]
    log = _run("ffmpeg", [*args, "-f", "null", "-"]).stderr
    lufs = re.findall(r"\bI:\s*(-?[\d.]+)\s*LUFS", log)
    peaks = re.findall(r"Peak:\s*(-?(?:[\d.]+|inf))\s*dBFS", log)
    frames = _frames(path)
    motions = [_difference(a, b) for a, b in zip(frames, frames[1:])]
    fingerprints = [_hash(frame) for frame in _frames(path, fps=1, size="9:8", crop="crop=iw:ih*0.60:0:0")]
    return {"width": video.get("width"), "height": video.get("height"), "duration": duration,
            "audio_present": bool(audio), "lufs": float(lufs[-1]) if lufs else None,
            "peak_dbfs": float(peaks[-1]) if peaks else None,
            "black": _intervals(log, "black", duration),
            "frozen": _intervals(log, "freeze", duration),
            "silence": _intervals(log, "silence", duration),
            "motion": sum(motions) / max(1, len(motions)),
            "hook_motion": max(motions[:3], default=0), "hashes": fingerprints}


def caption_evidence(clip):
    if not clip.base_path or not Path(clip.base_path).is_file():
        return 0.0
    words = [w for w in clip.caption_words if str(w.get("word", "")).strip() and float(w["end"]) > float(w["start"])]
    if not words:
        return 0.0
    # Sample throughout the clip, at the middle of actual caption intervals.
    sample = [words[i] for i in sorted({round(i * (len(words) - 1) / min(11, max(1, len(words) - 1)))
                                       for i in range(min(12, len(words)))})]
    passed = 0
    for word in sample:
        at = (float(word["start"]) + float(word["end"])) / 2
        a, b = _frame(clip.base_path, at), _frame(clip.path, at)
        # Lower-middle safe area used by all caption styles. Compare strong
        # localized changes, not whole-file hashes or encoder noise.
        start, end = 270 * 280, 270 * 380
        inside = sum(abs(x-y) > 35 for x, y in zip(a[start:end], b[start:end])) / (end-start)
        outside = sum(abs(x-y) > 35 for x, y in zip(a[:270*240], b[:270*240])) / (270*240)
        passed += inside > max(.001, outside * 3)
    return passed / len(sample)


def _transcript(words):
    return " ".join(re.findall(r"\w+", " ".join(str(w.get("word", "")) for w in words).casefold()))


def _similar_hashes(left, right):
    if not left or not right:
        return False
    # Compare every sampled frame to handle small trims and cross-source reuploads.
    matches = sum(min((int(a, 16) ^ int(b, 16)).bit_count() for b in right) <= 6 for a in left)
    return matches / len(left) >= .85


def evaluate_quality(clip, checklist, config, ledger):
    reasons, signals = [], {}
    score = 0
    try:
        signals = inspect_media(clip.path)
        duration = signals["duration"]
        if (signals["width"], signals["height"]) != (1080, 1920):
            reasons.append("render is not 1080x1920")
        if not float(checklist.get("min_length_s", 0)) <= duration <= float(checklist.get("max_length_s", 58)) + .05:
            reasons.append("rendered length outside campaign limits")
        if abs(duration - (clip.end_s - clip.start_s)) > .25:
            reasons.append("rendered length differs from source segment")
        for kind in ("black", "frozen"):
            if any(end-start >= 2 for start, end in signals[kind]):
                reasons.append(f"long {kind} frames (at least 2 seconds)")
        if clip.base_path and Path(clip.base_path).resolve() != Path(clip.path).resolve():
            base_log = _run("ffmpeg", ["-hide_banner", "-nostats", "-i", clip.base_path,
                            "-vf", "blackdetect=d=2:pix_th=0.10,freezedetect=n=-50dB:d=2",
                            "-an", "-f", "null", "-"]).stderr
            for kind, prefix in (("black", "black"), ("frozen", "freeze")):
                if any(end-start >= 2 for start, end in _intervals(base_log, prefix, duration)):
                    reasons.append(f"long {kind} frames in base content (captions do not count as motion)")
        if not signals["audio_present"]:
            reasons.append("audio is missing")
        lufs = signals["lufs"]
        if lufs is None or not float(config.get("min_lufs", -18)) <= lufs <= float(config.get("max_lufs", -14)):
            reasons.append("audio loudness outside configured range")
        if signals["peak_dbfs"] is None or signals["peak_dbfs"] >= -.1:
            reasons.append("audio clipping or unmeasurable true peak")
        if any(start <= .1 and end-start > 2 for start, end in signals["silence"]):
            reasons.append("silence exceeds 2 seconds at start")
        words = clip.caption_words
        valid_words = [w for w in words if re.search(r"[A-Za-z]{2,}", str(w.get("word", "")))
                       and float(w.get("probability", 1)) >= .5]
        early = [w for w in valid_words if float(w["start"]) < 2]
        meaningful = len(set(_transcript(valid_words).split())) >= 3
        if not meaningful:
            reasons.append("meaningful speech transcript is missing")
        if not (len(early) >= 2 or signals["hook_motion"] >= 1.0):
            reasons.append("hook missing meaningful speech or motion in first 2 seconds")
        for w in words:
            if not 0 <= float(w["start"]) < float(w["end"]) <= duration + .05:
                reasons.append("caption timing outside rendered clip")
                break
        coverage = caption_evidence(clip)
        signals["caption_coverage"] = coverage
        if coverage < .8:
            reasons.append("burned-in captions not verified by frame diff against base")
        metadata = clip.title + "\n" + clip.description
        for tag in checklist.get("required_tags", []):
            if not re.search(re.escape(tag) + r"(?!\w)", metadata, re.I):
                reasons.append("required tags missing from title/description: " + tag)
        transcript = _transcript(words)
        for banned in checklist.get("banned_content", []):
            if banned and re.search(r"\b" + re.escape(banned) + r"\b", transcript, re.I):
                reasons.append("banned transcript topic: " + banned)
        brand = checklist.get("brand_spelling", "")
        brands = checklist.get("brand_spellings", []) or ([brand] if brand else [])
        for spelling in brands:
            for token in re.findall(r"[\w'-]+", " ".join(str(w.get("word", "")) for w in words)):
                if len(token) >= 3 and len(spelling) >= 3 and SequenceMatcher(None, token.casefold(), spelling.casefold()).ratio() >= .8 and token != spelling:
                    reasons.append(f"caption brand spelling: {token} must be {spelling}")
        speech_seconds = 0.0
        previous_end = 0.0
        for word in sorted(valid_words, key=lambda w: float(w["start"])):
            start, end = max(0, float(word["start"])), min(duration, float(word["end"]))
            speech_seconds += max(0, end - max(start, previous_end))
            previous_end = max(previous_end, end)
        density = min(1.0, speech_seconds / duration)
        thought = bool(words and re.search(r"[.!?][\"']?$", str(words[-1].get("word", "")).strip()))
        components = {"hook_strength": 25 * min(1, max(len(early)/3, signals["hook_motion"]/3)),
                      "speech_density": 25 * min(1, density/.65),
                      "caption_coverage": 20 * coverage,
                      "visual_motion": 15 * min(1, signals["motion"]/3),
                      "completeness_of_thought": 15 if thought else 4}
        score = round(sum(components.values()))
        signals.update(components=components, transcript=transcript, speech_density=density)
        for other in ledger.quality_reference_clips(except_clip_id=clip.id):
            if other["source_id"] == clip.source_id and min(clip.end_s, other["end_s"]) > max(clip.start_s, other["start_s"]):
                reasons.append("source segment overlap across stocked/posted clips: " + other["id"])
            prior = other.get("quality", {}).get("signals", {})
            hashes = prior.get("hashes")
            if not hashes:
                try:
                    hashes = inspect_media(other["path"])["hashes"]
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                    reasons.append("duplicate comparison unavailable for existing clip: " + other["id"])
            prior_text = prior.get("transcript") or _transcript(other.get("caption_words", []))
            if not prior_text:
                reasons.append("duplicate transcript comparison unavailable for existing clip: " + other["id"])
            similar_text = bool(transcript and prior_text and SequenceMatcher(None, transcript, prior_text).ratio() >= .88)
            if _similar_hashes(signals["hashes"], hashes) or similar_text:
                reasons.append("near-duplicate perceptual hash or transcript: " + other["id"])
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        reasons.append(f"quality evidence unavailable: {type(exc).__name__}: {str(exc)[:300]}")
    minimum = max(0, min(100, int(config.get("min_quality", 70))))
    if score < minimum:
        reasons.append(f"quality score {score} below minimum {minimum}")
    return {"passed": not reasons, "score": score, "reasons": list(dict.fromkeys(reasons)), "signals": signals}


def feedback_summary(ledger):
    path = ledger.home / "whop_results.csv"
    if not path.exists():
        with path.open("x", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerow(["clip_id", "status", "reason"])
    latest = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            clip_id = (row.get("clip_id") or "").strip()
            clip = ledger.clip(clip_id)
            if clip:
                latest[clip_id] = (clip["campaign_id"], (row.get("status") or "").strip().lower(), (row.get("reason") or "").strip())
    result = {}
    for clip_id, (campaign, status, reason) in latest.items():
        if status not in {"rejected", "accepted", "approved", "flagged"}:
            continue
        ledger.event("whop_owner_result", {"clip_id": clip_id, "campaign_id": campaign, "status": status, "reason": reason},
                     "whop-result:" + hashlib.sha256(json.dumps([clip_id, status, reason]).encode()).hexdigest())
        row = result.setdefault(campaign, {"accepted": 0, "rejected": 0, "reasons": [], "factor": 1.0})
        row["rejected" if status in {"rejected", "flagged"} else "accepted"] += 1
        if status in {"rejected", "flagged"} and reason:
            row["reasons"].append(reason)
    for row in result.values():
        row["factor"] = (row["accepted"] + 1) / (row["accepted"] + row["rejected"] + 1)
    return result


def record_review(ledger, clip, result, status):
    thumbnails = []
    for fraction in (.15, .5, .85):
        try:
            data = _run("ffmpeg", ["-v", "error", "-ss", str((clip.end_s-clip.start_s)*fraction), "-i", clip.path,
                                    "-frames:v", "1", "-vf", "scale=135:240", "-f", "image2pipe", "-c:v", "mjpeg", "-threads", "1", "-"], binary_output=True).stdout
            thumbnails.append(base64.b64encode(data).decode())
        except (OSError, RuntimeError, subprocess.SubprocessError):
            break
    ledger.event("quality_review", {"day": quota_day().isoformat(), "clip_id": clip.id, "campaign_id": clip.campaign_id,
                 "channel": clip.channel_handle, "title": clip.title, "description": clip.description,
                 "score": result.get("score", 0), "reasons": result.get("reasons", []),
                 "components": result.get("signals", {}).get("components", {}), "status": status, "thumbnails": thumbnails})
    return render_review(ledger)


def render_review(ledger):
    directory = ledger.home / "review"
    directory.mkdir(exist_ok=True)
    groups = {quota_day().isoformat(): {}}
    for event in ledger.events():
        if event["kind"] == "quality_review":
            row = event["details"]
            groups.setdefault(row["day"], {})[(row["clip_id"], row["status"], row["channel"])] = row
    for day, rows in groups.items():
        parts = ["<!doctype html><meta charset='utf-8'><title>Daily clip review</title>",
                 "<h1>Daily clip review — " + html.escape(day) + "</h1>"]
        for row in rows.values():
            esc = lambda key: html.escape(str(row.get(key, "")))
            parts.append(f"<article><h2>{esc('title')}</h2><p>{esc('status')} · {esc('clip_id')} · {esc('channel')} · score {esc('score')}/100</p>")
            parts.extend(f"<img alt='Clip thumbnail' width='135' height='240' src='data:image/jpeg;base64,{thumb}'>" for thumb in row["thumbnails"])
            if not row["thumbnails"]:
                parts.append("<p>Thumbnail unavailable: media could not be decoded.</p>")
            parts.append("<pre>" + esc("description") + "</pre><ul>" + "".join("<li>" + html.escape(str(reason)) + "</li>" for reason in row["reasons"]) + "</ul></article>")
            parts.append("<p>" + html.escape(", ".join(f"{key.replace('_', ' ')}: {value:.1f}" for key, value in row.get("components", {}).items())) + "</p>")
        target = directory / (day + ".html")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False) as stream:
            stream.write("\n".join(parts))
            temporary = Path(stream.name)
        temporary.replace(target)
    return directory / (quota_day().isoformat() + ".html")
