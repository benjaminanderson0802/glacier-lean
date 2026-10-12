"""Real local media fixtures for producer and distributor regressions."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def caption_words(duration_s: float = 25, variant: int = 0):
    phrases = [
        "Watch this useful example change everything right now as the bright opening gives way to a clear result with helpful details and a practical explanation everyone can follow from start to finish.",
        "See how the bright orange block moves across this screen while each simple step builds toward a useful answer that makes the whole process easier to understand and remember later.",
        "Notice every quiet blue shape shifting behind these words as the creator explains the product, shows the important moment, and finishes with a direct takeaway viewers can use today.",
        "Here is a completely different scene with a yellow square, moving patterns, and a short story that reveals exactly what changed and why the final result matters to people watching.",
    ]
    phrase = phrases[variant % len(phrases)].split()
    starts = [0.15, 0.75, 1.35]
    remaining = max(0, len(phrase) - len(starts))
    starts.extend(3.0 + i * (duration_s - 4.0) / max(1, remaining - 1)
                  for i in range(remaining))
    return [{"start": start, "end": min(duration_s - .05, start + .45), "word": word}
            for word, start in zip(phrase, starts)]


def generated_clip_media(directory: Path, name: str, *, duration_s: float = 25,
                         variant: int = 0):
    """Return a moving testsrc2/sine base and its captioned 1080x1920 render."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.skip("real ffmpeg and ffprobe are required for generated media fixtures")
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"{name}-base.mp4"
    output = directory / f"{name}.mp4"
    video_filter = f"testsrc2=s=1080x1920:r=12:d={duration_s}"
    if variant % 2:
        video_filter += ",negate"
    subprocess.run([
        ffmpeg, "-v", "error", "-f", "lavfi", "-i",
        video_filter,
        "-f", "lavfi", "-i", f"sine=frequency={440 + variant * 37}:duration={duration_s}",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-t", str(duration_s),
        "-c:v", "libx264", "-threads", "2", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-y", str(base),
    ], check=True, capture_output=True)

    from scripts.clipper import render_clip
    words = caption_words(duration_s, variant)
    rendered = render_clip(base, output, start_s=0, end_s=duration_s,
                           caption_words=words, mode="center_crop")
    return base, rendered, words
