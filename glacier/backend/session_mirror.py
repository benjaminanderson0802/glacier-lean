"""Read-only reader for local Codex CLI JSONL session logs."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import secrets_store

log = logging.getLogger(__name__)
MAX_OUTPUT = 4000
MAX_LINE_BYTES = 1_000_000
MAX_EVENTS = 2000
_FILE_CACHE: dict[tuple[str, int, int], tuple[dict, list[dict], str, bool]] = {}


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
            number = 0
            while True:
                raw = handle.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                number += 1
                digest.update(raw)
                if len(raw) > MAX_LINE_BYTES:
                    if warnings:
                        log.warning("Skipping over-long Codex session line %s:%d", path, number)
                    while raw and not raw.endswith(b"\n"):
                        raw = handle.readline(MAX_LINE_BYTES + 1)
                        digest.update(raw)
                    continue
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


def _file_signature(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path), stat.st_mtime_ns, stat.st_size


def _first_record_id(path: Path) -> str:
    """Choose the id using only the first record; old formats fall back to filename."""
    try:
        with path.open("rb") as handle:
            raw = handle.readline(MAX_LINE_BYTES + 1)
        if len(raw) <= MAX_LINE_BYTES:
            record = json.loads(raw)
            if isinstance(record, dict) and record.get("type") == "session_meta":
                payload = record.get("payload")
                if isinstance(payload, dict) and payload.get("id"):
                    return str(payload["id"])
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    return path.stem


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
    content = payload if payload else {key: value for key, value in record.items() if key != "timestamp"}
    return {"type": "other", "text": _text(content), "timestamp": stamp}


def _load_file(path: Path) -> tuple[dict, list[dict], str, bool] | None:
    signature = _file_signature(path)
    if signature is None:
        return None
    cached = _FILE_CACHE.get(signature)
    if cached is not None:
        return cached
    # Discard stale versions of this path while retaining independent file entries.
    path_key = signature[0]
    for key in list(_FILE_CACHE):
        if key[0] == path_key and key != signature:
            del _FILE_CACHE[key]

    meta = {}
    events = deque(maxlen=MAX_EVENTS)
    event_count = 0
    digest = ""
    max_time = None
    first_time = None
    for line_number, (record, final_digest) in enumerate(_records(path), 1):
        if final_digest:
            digest = final_digest
            continue
        if line_number == 1 and record.get("type") == "session_meta":
            meta = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        if "_glacier_digest" in record:
            continue
        created = _timestamp(record.get("timestamp"))
        if created and (first_time is None or created < first_time):
            first_time = created
        event = _event(record, created)
        if event:
            events.append(event)
            event_count += 1
        if created and (max_time is None or created > max_time):
            max_time = created
    try:
        fallback = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError:
        return None
    current_id = str(meta.get("id") or path.stem)
    started = _timestamp(meta.get("timestamp")) or first_time or fallback
    updated = max_time or fallback
    summary = {"id": current_id, "tool": "codex", "started": started.isoformat(), "updated": updated.isoformat(),
               "title": next((event["text"].strip()[:160] for event in events if event["type"] == "user_message" and event["text"].strip()), ""),
               "cwd": meta.get("cwd") or "", "active": (datetime.now(timezone.utc) - updated).total_seconds() <= 120,
               "truncated": event_count > MAX_EVENTS}
    parsed = (summary, list(events), digest, event_count > MAX_EVENTS)
    _FILE_CACHE[signature] = parsed
    return parsed


def _summary_copy(summary: dict) -> dict:
    result = dict(summary)
    updated = _timestamp(result.get("updated"))
    result["active"] = bool(updated and (datetime.now(timezone.utc) - updated).total_seconds() <= 120)
    return result


def read_session(session_id: str) -> tuple[dict, list[dict], str] | None:
    for path in _files():
        if _first_record_id(path) != session_id:
            continue
        parsed = _load_file(path)
        if parsed is None:
            return None
        summary, events, digest, _ = parsed
        return _summary_copy(summary), [dict(event) for event in events], digest
    return None


def list_sessions() -> list[dict]:
    result = []
    seen = set()
    for path in _files():
        parsed = _load_file(path)
        if parsed is None:
            continue
        summary = parsed[0]
        session_id = summary["id"]
        if session_id in seen:
            continue
        seen.add(session_id)
        result.append({key: _summary_copy(summary)[key] for key in ("id", "tool", "started", "updated", "title", "cwd", "active")})
    return sorted(result, key=lambda row: row["updated"], reverse=True)
