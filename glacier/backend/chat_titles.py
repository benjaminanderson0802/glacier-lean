"""Readable titles for mirrored CLI sessions, and which sessions are background automation.

Codex and Claude transcripts start with injected context (<environment_context>, <system-reminder>,
goal blocks, JSON content parts). Those are not what the owner typed, so they never become a title.
"""
from __future__ import annotations

import json
import os
import re
import tempfile

_LEADING_BLOCK = re.compile(r"\A\s*<([A-Za-z][\w-]*)\b[^>]*>.*?(?:</\1\s*>|\Z)", re.S)
_AUTOMATED_TITLE = re.compile(r"^(?:SMOKE TEST\b|Reply with exactly\b|You are the [A-Z][A-Z_ -]{2,}\b|Return ONLY\b)")


def _from_json_parts(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("[{"):
        return text
    try:
        parts = json.loads(stripped)
    except ValueError:
        # A truncated JSON preview: keep only the quoted text values we can see.
        return " ".join(re.findall(r'"text":\s*"((?:[^"\\]|\\.)*)', stripped)).encode().decode("unicode_escape", "ignore")
    if isinstance(parts, list):
        return " ".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    return text


def clean_title(text: str | None, limit: int = 160) -> str:
    """The owner's words with injected context blocks removed, on one line; '' when nothing is left."""
    value = _from_json_parts(str(text or ""))
    for _ in range(20):
        match = _LEADING_BLOCK.match(value)
        if not match:
            break
        value = value[match.end():]
    value = " ".join(value.split())
    return value[:limit]


def first_title(texts) -> str:
    return next((title for title in (clean_title(text) for text in texts) if title), "")


def _temp_roots() -> list[str]:
    roots = {tempfile.gettempdir(), "/tmp", os.environ.get("TEMP", ""), os.environ.get("TMP", "")}
    return [os.path.normcase(os.path.abspath(root)) for root in roots if root]


def is_automated(title: str, cwd: str | None) -> bool:
    """Background sessions: Glacier's own engine calls (temp folders), smoke tests, and role prompts."""
    if not title:
        return True
    if _AUTOMATED_TITLE.match(title):
        return True
    if cwd and os.path.isabs(cwd):
        folder = os.path.normcase(os.path.abspath(cwd))
        if any(folder == root or folder.startswith(root + os.sep) for root in _temp_roots()):
            return True
    if cwd and re.search(r"[\\/]appdata[\\/]local[\\/]temp[\\/]", cwd, re.I):
        return True
    return False
