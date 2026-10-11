"""CPU transcription, candidate scoring, captions, and ffmpeg rendering."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def _rules_keywords(rules_text: str):
    match = re.search(r"(?:keywords?|topics?)\s*[:=]\s*([^\n.]+)", rules_text, re.I)
    return [word.strip(" #,-").lower() for word in re.split(r"[,;]", match.group(1)) if word.strip()] if match else []


def score_candidate(text: str, duration: float, keywords=(), *, hook_text=None):
    words = re.findall(r"\b[\w'-]+\b", text.lower())
    if not 20 <= duration <= 58:
        return 0.0
    hook_words = re.findall(r"\b[\w'-]+\b", (hook_text if hook_text is not None else " ".join(words[:12])).lower())
    hook = bool(re.search(r"\b(why|how|what|watch|here'?s|this|never|first|secret|because|turns out)\b", " ".join(hook_words)))
    complete = text.rstrip().endswith((".", "!", "?", '.”', '!”', '?”'))
    normalized = " ".join(words)
    density = sum(1 for word in keywords if re.search(rf"\b{re.escape(word.lower())}\b", normalized)) / max(1, len(keywords))
    return min(1.0, 0.35 + (0.25 if hook else 0) + (0.2 if complete else 0) + min(0.2, density * 0.2))


def transcribe(source: Path, *, model_size="small", device="cpu", compute_type="int8"):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("transcription requires the open-source faster-whisper package") from exc
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(source), word_timestamps=True, vad_filter=True)
    output = []
    for segment in segments:
        output.append({"start": float(segment.start), "end": float(segment.end), "text": segment.text.strip(),
                       "words": [{"start": float(word.start), "end": float(word.end), "word": word.word.strip()}
                                 for word in (segment.words or [])]})
    return output, {"language": getattr(info, "language", None), "duration": getattr(info, "duration", None)}


def candidate_segments(transcript, source_id, rules_text="", *, min_s=20, max_s=58, llm_url="http://127.0.0.1:11434"):
    keywords = _rules_keywords(rules_text)
    result = []
    cursor = 0
    while cursor < len(transcript):
        start = transcript[cursor]["start"]
        end_idx = cursor
        text = ""
        while end_idx < len(transcript) and transcript[end_idx]["end"] - start <= max_s:
            text = (text + " " + transcript[end_idx]["text"]).strip()
            end_idx += 1
            duration = transcript[end_idx - 1]["end"] - start
            if duration >= min_s and text.endswith((".", "!", "?")):
                words = [word for row in transcript[cursor:end_idx] for word in row.get("words", [])]
                hook_text = " ".join(str(word.get("word", "")) for word in words
                                      if float(word.get("start", start)) < start + 3)
                result.append({"source_id": source_id, "start_s": start, "end_s": transcript[end_idx - 1]["end"],
                               "text": text, "words": words,
                               "score": score_candidate(text, duration, keywords, hook_text=hook_text)})
                cursor = end_idx
                break
        else:
            cursor += 1
            continue
        if cursor == end_idx:
            continue
    return score_with_ollama(result, llm_url=llm_url)


def score_with_ollama(candidates, *, llm_url="http://127.0.0.1:11434", model="granite3.3:2b", timeout=2):
    if not candidates:
        return candidates
    body = json.dumps({"model": model, "prompt": "Rate each clip transcript for a clear, complete short-video hook. Return only JSON {scores:[0..1]}.\n" +
                       json.dumps([item["text"] for item in candidates]), "stream": False,
                       "format": {"type": "object", "properties": {"scores": {"type": "array", "items": {"type": "number"}}}}}).encode("utf-8")
    request = urllib.request.Request(llm_url.rstrip("/") + "/api/generate", data=body,
                                    headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        scores = json.loads(result.get("response", "{}" )).get("scores", [])
        for item, score in zip(candidates, scores):
            item["score"] = round((item["score"] + max(0.0, min(1.0, float(score))) / 2), 4)
            item["scorer"] = model
    except (OSError, ValueError, KeyError, urllib.error.URLError, TypeError):
        for item in candidates:
            item["scorer"] = "heuristic"
    return candidates


def _ass_time(seconds):
    centis = max(0, int(seconds * 100))
    return f"{centis // 360000}:{(centis // 6000) % 60:02}:{(centis // 100) % 60:02}.{centis % 100:02}"


def write_word_captions(words, path: Path, style="bold_center"):
    style_options = {
        "bold_center": ("Arial", 66, "&H00FFFFFF", 2, 230),
        "clean_lower": ("Arial", 52, "&H00FFFFFF", 2, 120),
        "highlight_words": ("Arial", 72, "&H0000D7FF", 2, 250),
        "compact_top": ("Arial", 48, "&H00FFFFFF", 8, 100),
        "outline_center": ("Arial Black", 64, "&H00FFFFFF", 2, 210),
        "boxed_lower": ("Verdana", 54, "&H00FFFFFF", 2, 145),
        "two_line_center": ("Trebuchet MS", 62, "&H00FFFFCC", 2, 230),
        "minimal_bottom": ("Calibri", 50, "&H00FFFFFF", 2, 100),
        "emphasis_pulse": ("Arial Black", 68, "&H0000A5FF", 2, 260),
        "small_caps_top": ("Arial", 44, "&H00FFFFFF", 8, 110),
    }
    if isinstance(style, dict):
        font, size, primary, alignment, margin_v = style_options.get(style.get("caption", "bold_center"), style_options["bold_center"])
        base = style.get("base", style.get("base_color", primary))
        highlight = style.get("highlight", style.get("highlight_color", style.get("accent_color", "&H0000D7FF")))
        accent = style.get("accent_color", highlight)
        key_words = {str(word).lower() for word in style.get("key_words", [])}
    else:
        font, size, primary, alignment, margin_v = style_options.get(style, style_options["bold_center"])
        base, highlight, accent, key_words = primary, "&H0000D7FF", "&H0000D7FF", set()
    alignment, margin_v = 2, 500  # lower-middle safe area, above Shorts controls
    events = []
    for word in words or []:
        value = str(word.get("word", "")).replace("{", "").replace("}", "").strip()
        if value:
            clean = re.sub(r"[^\w'-]", "", value).lower()
            color = accent if clean in key_words else highlight
            text = f"{{\\c{color}&}}{value}{{\\c{base}&}}"
            events.append(f"Dialogue: 0,{_ass_time(word['start'])},{_ass_time(word['end'])},Caption,,0,0,0,,{text}")
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{size},{base},&H00000000,-1,0,1,4,2,{alignment},72,72,{margin_v},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"
    path.write_text(content, encoding="utf-8")


def render_clip(source: Path, target: Path, *, start_s: float, end_s: float, caption_words=(),
                mode="blurred_background", caption_style="bold_center"):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg executable is required for rendering")
    if end_s <= start_s:
        raise ValueError("clip end must follow clip start")
    target.parent.mkdir(parents=True, exist_ok=True)
    args = [ffmpeg, "-v", "error", "-ss", str(start_s), "-i", str(source), "-t", str(end_s-start_s)]
    if mode == "center_crop":
        video_filter = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        video_filter = ("[0:v]split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
                        "crop=1080:1920,boxblur=24:8[blur];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];"
                        "[blur][front]overlay=(W-w)/2:(H-h)/2")
    if caption_words:
        ass_path = target.with_suffix(".ass")
        write_word_captions(caption_words, ass_path, caption_style)
        escaped = ass_path.as_posix().replace(":", "\\:").replace("'", "\\'")
        video_filter += f",ass='{escaped}'"
    video_filter += "[outv]"
    args += ["-filter_complex", video_filter, "-map", "[outv]", "-map", "0:a?", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-y", str(target)]
    subprocess.run(args, check=True, timeout=max(60, int((end_s-start_s) * 10)))
    return target


def make_clip(source: Path, target: Path, segment: dict, *, requires_editing=True, caption_words=True,
              mode="blurred_background", caption_style="bold_center"):
    if not requires_editing:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target
    words = []
    if caption_words:
        for word in segment.get("words", []):
            start = max(0.0, float(word["start"]) - float(segment["start_s"]))
            end = min(float(segment["end_s"]) - float(segment["start_s"]),
                      float(word["end"]) - float(segment["start_s"]))
            if end > start:
                words.append({**word, "start": start, "end": end})
    return render_clip(source, target, start_s=segment["start_s"], end_s=segment["end_s"],
                       caption_words=words, mode=mode, caption_style=caption_style)
