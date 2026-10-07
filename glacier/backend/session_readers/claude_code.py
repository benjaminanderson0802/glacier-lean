"""Read-only reader for Claude Code project JSONL transcripts."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)
MAX_LINE_BYTES = 1_000_000
MAX_EVENTS = 2000


def data_dir() -> Path:
    return Path(os.path.expandvars(os.path.expanduser(os.environ.get("GLACIER_CLAUDE_CODE_DATA", "~/.claude"))))


def _timestamp(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
    except ValueError:
        return None


def _text(value) -> str:
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)[:4000]
    return ""


def _records(path: Path) -> Iterator[dict]:
    try:
        with path.open("rb") as handle:
            number = 0
            while True:
                raw = handle.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                number += 1
                if len(raw) > MAX_LINE_BYTES:
                    log.warning("Skipping over-long Claude Code session line %s:%d", path, number)
                    while raw and not raw.endswith(b"\n"):
                        raw = handle.readline(MAX_LINE_BYTES + 1)
                    continue
                try:
                    record = json.loads(raw)
                    if not isinstance(record, dict):
                        raise ValueError("record is not an object")
                except (ValueError, UnicodeDecodeError):
                    log.warning("Skipping malformed Claude Code session line %s:%d", path, number)
                    continue
                yield record
    except OSError as exc:
        log.warning("Could not read Claude Code session file %s: %s", path, exc)


def _files() -> Iterator[Path]:
    root = data_dir() / "projects"
    if not root.is_dir():
        return
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            if name.endswith(".jsonl"):
                yield Path(base) / name


def _identity(path: Path, records: list[dict]) -> tuple[str, str, str]:
    first = records[0] if records else {}
    raw_id = first.get("sessionId") or path.stem
    cwd = next((str(record.get("cwd")) for record in records if record.get("cwd")), "")
    return str(raw_id), cwd, "Claude Code session"


def _content(record: dict):
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return content if isinstance(content, list) else ([{"type": "text", "text": content}] if isinstance(content, str) else [])


def _parse(path: Path, include_events: bool):
    digest = hashlib.sha256()
    records = []
    try:
        with path.open("rb") as handle:
            number = 0
            while True:
                raw = handle.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                digest.update(raw)
                number += 1
                if len(raw) > MAX_LINE_BYTES:
                    log.warning("Skipping over-long Claude Code session line %s:%d", path, number)
                    while raw and not raw.endswith(b"\n"):
                        raw = handle.readline(MAX_LINE_BYTES + 1)
                        digest.update(raw)
                    continue
                try:
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError("record is not an object")
                except (ValueError, UnicodeDecodeError):
                    log.warning("Skipping malformed Claude Code session line %s:%d", path, number)
                    continue
                records.append(value)
    except OSError as exc:
        log.warning("Could not read Claude Code session file %s: %s", path, exc)
        return None
    raw_id, cwd, _ = _identity(path, records)
    if not records:
        return None
    events = []
    timestamps = []
    user_title = ""
    for record in records:
        stamp = _timestamp(record.get("timestamp"))
        if stamp:
            timestamps.append(stamp)
        if not include_events:
            if not user_title and record.get("type") == "user":
                user_title = _text(record.get("message", {}).get("content") if isinstance(record.get("message"), dict) else "").strip()[:160]
            continue
        kind = record.get("type")
        for part in _content(record):
            part_type = part.get("type") if isinstance(part, dict) else None
            if kind == "user" and part_type == "text":
                text = _text(part.get("text"))
                if text:
                    events.append({"type": "user_message", "text": text, "timestamp": stamp.isoformat() if stamp else None})
            elif kind == "user" and part_type == "tool_result":
                result = _text(part.get("content"))
                if result:
                    events.append({"type": "command_output", "text": result, "timestamp": stamp.isoformat() if stamp else None})
            elif kind == "assistant" and part_type == "text":
                text = _text(part.get("text"))
                if text:
                    events.append({"type": "assistant_message", "text": text, "timestamp": stamp.isoformat() if stamp else None})
            elif kind == "assistant" and part_type == "tool_use":
                tool = str(part.get("name") or "tool")
                inp = part.get("input") if isinstance(part.get("input"), dict) else {}
                shown = inp.get("command") or inp.get("description") or tool
                events.append({"type": "command", "text": f"Ran command: {_text(shown)}", "timestamp": stamp.isoformat() if stamp else None})
    fallback = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    started = timestamps[0] if timestamps else fallback
    updated = timestamps[-1] if timestamps else fallback
    if user_title:
        title = user_title
    elif include_events:
        title = next((event["text"][:160] for event in events if event["type"] == "user_message"), "Claude Code session")
    else:
        title = "Claude Code session"
    summary = {"id": f"claude-code:{raw_id}", "tool": "claude-code", "source": "claude", "started": started.isoformat(),
               "updated": updated.isoformat(), "title": title, "cwd": cwd,
               "active": (datetime.now(timezone.utc) - updated).total_seconds() <= 120}
    events.sort(key=lambda event: (event.get("timestamp") or "", 0))
    truncated = len(events) > MAX_EVENTS
    if truncated:
        events = events[-MAX_EVENTS:]
    if include_events:
        summary["truncated"] = truncated
    return summary, events if include_events else [], digest.hexdigest()


def list_sessions() -> list[dict]:
    result = []
    seen = set()
    for path in _files():
        parsed = _parse(path, include_events=False)
        if parsed is None:
            continue
        summary = parsed[0]
        if summary["id"] in seen:
            continue
        seen.add(summary["id"])
        result.append({key: summary[key] for key in ("id", "tool", "source", "started", "updated", "title", "cwd", "active")})
    return result


def read_session(session_id: str):
    if not session_id.startswith("claude-code:"):
        return None
    for path in _files():
        parsed = _parse(path, include_events=True)
        if parsed and parsed[0]["id"] == session_id:
            return parsed
    return None
