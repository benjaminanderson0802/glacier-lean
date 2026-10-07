"""Read-only reader for Gemini CLI local JSON session logs and checkpoints."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)
MAX_FILE_BYTES = 20_000_000
MAX_EVENTS = 2000


def data_dir() -> Path:
    return Path(os.path.expandvars(os.path.expanduser(os.environ.get("GLACIER_GEMINI_DATA", "~/.gemini"))))


def _timestamp(value) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str) and value:
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _text(value) -> str:
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, list):
        return "\n".join(_text(item.get("text", "") if isinstance(item, dict) else item) for item in value)[:4000]
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)[:4000]
    return ""


def _files() -> Iterator[Path]:
    root = data_dir() / "tmp"
    if not root.is_dir():
        return
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            path = Path(base) / name
            if path.suffix == ".json" and (path.parent.name in ("chats", "checkpoints") or name.startswith("checkpoint-")):
                yield path


def _load(path: Path):
    try:
        stat = path.stat()
        if stat.st_size > MAX_FILE_BYTES:
            raise ValueError("session file exceeds size limit")
        raw = path.read_bytes()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("session is not an object")
        return value, hashlib.sha256(raw).hexdigest(), stat
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        log.warning("Skipping malformed Gemini CLI session file %s: %s", path, exc)
        return None


def _message_text(message: dict) -> str:
    return _text(message.get("content") or message.get("text") or message.get("parts") or "")


def _session_id(path: Path, payload: dict) -> str:
    value = payload.get("sessionId") or payload.get("id") or payload.get("chatId")
    return str(value or path.stem.removeprefix("checkpoint-"))


def _parse(path: Path, include_events: bool):
    loaded = _load(path)
    if not loaded:
        return None
    payload, digest, stat = loaded
    messages = payload.get("messages") or payload.get("history") or payload.get("conversation")
    if not isinstance(messages, list):
        # Gemini's checkpoint files wrap the serialized conversation state.
        messages = payload.get("chat")
        if isinstance(messages, dict):
            messages = messages.get("messages") or messages.get("history")
    if not isinstance(messages, list):
        log.warning("Skipping malformed Gemini CLI session file %s: no message list", path)
        return None
    events = []
    stamps = []
    title = ""
    for message in messages:
        if not isinstance(message, dict):
            continue
        stamp = _timestamp(message.get("timestamp") or message.get("createdAt") or message.get("time"))
        if stamp:
            stamps.append(stamp)
        role = str(message.get("type") or message.get("role") or "").lower()
        text = _message_text(message)
        if role in ("user", "human"):
            if not title and text.strip():
                title = text.strip()[:160]
            if include_events and text:
                events.append({"type": "user_message", "text": text, "timestamp": stamp.isoformat() if stamp else None})
        elif role in ("gemini", "model", "assistant"):
            tool_calls = message.get("toolCalls") or message.get("tool_calls") or []
            if include_events and isinstance(tool_calls, list):
                for call in tool_calls:
                    if not isinstance(call, dict):
                        continue
                    name = str(call.get("name") or call.get("toolName") or "tool")
                    args = call.get("args") if isinstance(call.get("args"), dict) else {}
                    command = args.get("command") or args.get("cmd") or args.get("description") or name
                    events.append({"type": "command", "text": f"Ran command: {_text(command)}", "timestamp": stamp.isoformat() if stamp else None, "_order": -2, "_message_order": len(events)})
                    result = call.get("result")
                    if result:
                        if isinstance(result, dict):
                            result = result.get("llmContent") or result.get("output") or result.get("content") or result
                        events.append({"type": "command_output", "text": _text(result), "timestamp": stamp.isoformat() if stamp else None, "_order": -1, "_message_order": len(events)})
            if include_events and text:
                events.append({"type": "assistant_message", "text": text, "timestamp": stamp.isoformat() if stamp else None, "_order": 0, "_message_order": len(events)})
    started = _timestamp(payload.get("startTime") or payload.get("createdAt")) or (stamps[0] if stamps else datetime.fromtimestamp(stat.st_mtime, timezone.utc))
    updated = _timestamp(payload.get("lastUpdated") or payload.get("updatedAt")) or (stamps[-1] if stamps else datetime.fromtimestamp(stat.st_mtime, timezone.utc))
    raw_id = _session_id(path, payload)
    summary = {"id": f"gemini:{raw_id}", "tool": "gemini", "source": "gemini", "started": started.isoformat(),
               "updated": updated.isoformat(), "title": title or "Gemini CLI session",
               "cwd": str(payload.get("cwd") or payload.get("projectRoot") or ""),
               "active": (datetime.now(timezone.utc) - updated).total_seconds() <= 120}
    events.sort(key=lambda event: (event.get("timestamp") or "", event.get("_message_order", 0), event.get("_order", 0)))
    for event in events:
        event.pop("_order", None)
        event.pop("_message_order", None)
    truncated = len(events) > MAX_EVENTS
    if truncated:
        events = events[-MAX_EVENTS:]
    if include_events:
        summary["truncated"] = truncated
    return summary, events if include_events else [], digest


def list_sessions() -> list[dict]:
    result = []
    seen = set()
    for path in _files():
        parsed = _parse(path, include_events=False)
        if not parsed:
            continue
        summary = parsed[0]
        if summary["id"] in seen:
            continue
        seen.add(summary["id"])
        result.append({key: summary[key] for key in ("id", "tool", "source", "started", "updated", "title", "cwd", "active")})
    return result


def read_session(session_id: str):
    if not session_id.startswith("gemini:"):
        return None
    for path in _files():
        parsed = _parse(path, include_events=True)
        if parsed and parsed[0]["id"] == session_id:
            return parsed
    return None
