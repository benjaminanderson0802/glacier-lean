"""Read-only reader for local Codex CLI JSONL session logs."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import secrets_store

log = logging.getLogger(__name__)
MAX_OUTPUT = 4000


def sessions_dir() -> Path:
    return Path(os.path.expanduser(os.environ.get("GLACIER_CODEX_SESSIONS", "~/.codex/sessions")))


def _timestamp(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except ValueError:
        return None


def _text(value) -> str:
    if isinstance(value, str):
        return value[:MAX_OUTPUT]
    if isinstance(value, list):
        return "\n".join(_text(item.get("text", "") if isinstance(item, dict) else item) for item in value)[:MAX_OUTPUT]
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)[:MAX_OUTPUT]
    return str(value or "")[:MAX_OUTPUT]


def _records(path: Path, warnings: bool = True) -> Iterator[tuple[dict, str]]:
    """Yield decoded JSONL records and update a streaming content digest."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for number, raw in enumerate(handle, 1):
                digest.update(raw)
                try:
                    record = json.loads(raw)
                    if not isinstance(record, dict):
                        raise ValueError("record is not an object")
                except (ValueError, UnicodeDecodeError):
                    if warnings:
                        log.warning("Skipping malformed Codex session line %s:%d", path, number)
                    continue
                yield record, ""
    except OSError as exc:
        if warnings:
            log.warning("Could not read Codex session file %s: %s", path, exc)
        return
    yield {"_glacier_digest": digest.hexdigest()}, digest.hexdigest()


def _files() -> Iterator[Path]:
    root = sessions_dir()
    if not root.is_dir():
        return
    for base, dirs, names in os.walk(root):
        dirs.sort()
        for name in sorted(names):
            if name.endswith(".jsonl"):
                yield Path(base) / name


def _event(record: dict, when: datetime | None) -> dict | None:
    outer = str(record.get("type") or "other")
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    kind = str(payload.get("type") or outer)
    timestamp = _timestamp(record.get("timestamp")) or when
    stamp = timestamp.isoformat() if timestamp else None
    if kind in ("user_message", "user_input"):
        return {"type": "user_message", "text": _text(payload.get("message") or payload.get("text")), "timestamp": stamp}
    if kind in ("agent_message", "assistant_message"):
        return {"type": "assistant_message", "text": _text(payload.get("message") or payload.get("text")), "timestamp": stamp}
    if outer == "response_item" and kind == "message":
        role = payload.get("role")
        if role in ("user", "assistant"):
            text = _text(payload.get("content", ""))
            return {"type": "user_message" if role == "user" else "assistant_message", "text": text, "timestamp": stamp}
    if kind in ("function_call", "command_execution"):
        name = payload.get("name") or payload.get("command") or "command"
        args = payload.get("arguments")
        try:
            args = json.loads(args) if isinstance(args, str) else args
        except ValueError:
            pass
        command = args.get("cmd") if isinstance(args, dict) else args
        command = command or payload.get("command") or name
        exit_code = payload.get("exit_code")
        text = f"Ran command: {_text(command)}" + (f" (exit code {exit_code})" if exit_code is not None else "")
        return {"type": "command", "text": text, "exit_code": exit_code, "timestamp": stamp}
    if kind in ("function_call_output", "command_output"):
        return {"type": "command_output", "text": _text(payload.get("output") or payload.get("text")),
                "exit_code": payload.get("exit_code"), "timestamp": stamp}
    if kind in ("patch", "file_change", "apply_patch") or outer in ("patch_applied", "file_change"):
        changes = payload.get("changes") or payload.get("files") or payload.get("patch") or payload
        names = list(changes) if isinstance(changes, dict) else []
        return {"type": "file_change", "text": "Changed files: " + (", ".join(map(str, names)) or _text(changes)), "timestamp": stamp}
    if outer in ("session_meta", "turn_context"):
        return None
    return {"type": "other", "text": kind if kind != outer else outer, "timestamp": stamp}


def read_session(session_id: str) -> tuple[dict, list[dict], str] | None:
    for path in _files():
        meta = {}
        events = []
        digest = ""
        max_time = None
        for record, final_digest in _records(path):
            if final_digest:
                digest = final_digest
                continue
            if record.get("type") == "session_meta":
                meta = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            created = _timestamp(record.get("timestamp"))
            event = _event(record, created)
            if event:
                events.append(event)
            if created and (max_time is None or created > max_time):
                max_time = created
        current_id = str(meta.get("id") or path.stem)
        if current_id != session_id:
            continue
        started = _timestamp(meta.get("timestamp")) or next((_timestamp(event["timestamp"]) for event in events if event.get("timestamp")), None)
        updated = max_time or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        summary = {"id": current_id, "tool": "codex", "started": started.isoformat() if started else None,
                   "updated": updated.isoformat(), "title": "", "cwd": meta.get("cwd") or "",
                   "active": (datetime.now(timezone.utc) - updated).total_seconds() <= 120}
        summary["title"] = next((event["text"].strip()[:160] for event in events if event["type"] == "user_message" and event["text"].strip()), "")
        return summary, events, digest
    return None


def list_sessions() -> list[dict]:
    result = []
    seen = set()
    for path in _files():
        meta = {}
        last = None
        first = None
        first_user = ""
        for record, _ in _records(path):
            if record.get("type") == "session_meta":
                meta = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            timestamp = _timestamp(record.get("timestamp"))
            if timestamp and (first is None or timestamp < first):
                first = timestamp
            if timestamp and (last is None or timestamp > last):
                last = timestamp
            event = _event(record, timestamp)
            if not first_user and event and event["type"] == "user_message":
                first_user = event["text"].strip()[:160]
        session_id = str(meta.get("id") or path.stem)
        if session_id in seen:
            continue
        seen.add(session_id)
        try:
            fallback = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            continue
        started = _timestamp(meta.get("timestamp")) or first or fallback
        updated = last or fallback
        result.append({"id": session_id, "tool": "codex", "started": started.isoformat(), "updated": updated.isoformat(),
                       "title": first_user, "cwd": meta.get("cwd") or "",
                       "active": (datetime.now(timezone.utc) - updated).total_seconds() <= 120})
    return sorted(result, key=lambda row: row["updated"], reverse=True)
