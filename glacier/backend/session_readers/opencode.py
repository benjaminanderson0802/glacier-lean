"""Read-only reader for OpenCode v1.18.34 SQLite session storage."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger(__name__)
DB_TIMEOUT_SECONDS = 0.15
MAX_EVENTS = 2000
_FILE_CACHE: dict[tuple[str, int, int], list[dict]] = {}
_CACHE_LOCK = threading.RLock()


def data_dir() -> Path:
    override = os.environ.get("GLACIER_OPENCODE_DATA")
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override)))
    home = Path.home()
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        base = Path(os.path.expandvars(os.path.expanduser(xdg_data_home)))
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
    else:
        base = home / ".local" / "share"
    return base / "opencode"


def database_path() -> Path:
    return data_dir() / "opencode.db"


def _connect() -> sqlite3.Connection:
    path = database_path()
    if not path.is_file():
        raise FileNotFoundError(path)
    uri = "file:" + quote(str(path.resolve()), safe="/:") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=DB_TIMEOUT_SECONDS)


def _warning(exc: Exception) -> None:
    log.warning("Could not read OpenCode session database: %s", exc)


def _signature(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path), stat.st_mtime_ns, stat.st_size


def _iso(value) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def _json(value):
    try:
        return json.loads(value) if isinstance(value, str) else {}
    except (ValueError, TypeError):
        return None


def _text(value) -> str:
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)[:4000]
    return ""


def _part_event(part: dict, when: str | None) -> dict | None:
    kind = part.get("type")
    if kind == "text":
        text = part.get("text")
        if not isinstance(text, str) or part.get("synthetic") or part.get("ignored"):
            return None
        return {"type": "_text", "text": _text(text), "timestamp": when}
    if kind == "tool":
        tool = str(part.get("tool") or "tool")
        state = part.get("state") if isinstance(part.get("state"), dict) else {}
        input_data = state.get("input") if isinstance(state.get("input"), dict) else {}
        command = input_data.get("command") or input_data.get("cmd") or input_data
        shown = state.get("title") or command or tool
        events = [{"type": "command", "text": f"Ran command: {_text(shown)}", "timestamp": when}]
        if state.get("status") in ("completed", "error"):
            output = state.get("output") or state.get("error")
            if output:
                events.append({"type": "command_output", "text": _text(output), "timestamp": when})
        return {"type": "_many", "events": events}
    if kind == "patch":
        files = part.get("files") or []
        names = [str(item) for item in files] if isinstance(files, list) else []
        return {"type": "file_change", "text": "Changed files: " + (", ".join(names) or "files"), "timestamp": when}
    return None


_EVENT_ORDER = {"user_message": 0, "command": 1, "command_output": 2, "file_change": 3, "assistant_message": 4}


def _parse_v2(connection: sqlite3.Connection, session: dict, include_events: bool) -> tuple[dict, list[dict], str]:
    session_id = session["id"]
    rows = connection.execute(
        "SELECT id, type, time_created, data FROM session_message WHERE session_id = ? ORDER BY seq", (session_id,)
    ).fetchall()
    user_title = None
    first_time = None
    last_time = None
    events = []
    for message_id, role, created, raw_data in rows:
        message_data = _json(raw_data)
        if not isinstance(message_data, dict):
            raise ValueError(f"malformed OpenCode message {message_id}")
        stamp = _iso(created)
        first_time = min(filter(None, [first_time, stamp]), default=None)
        last_time = max(filter(None, [last_time, stamp]), default=None)
        if not include_events:
            if role != "user" or user_title is not None:
                continue
            part_rows = connection.execute(
                "SELECT data FROM part WHERE message_id = ? AND type = 'text' ORDER BY time_created, id LIMIT 1", (message_id,)
            ).fetchall()
        else:
            part_rows = connection.execute(
                "SELECT data FROM part WHERE message_id = ? ORDER BY time_created, id", (message_id,)
            ).fetchall()
        message_text = []
        tool_events = []
        for (raw_part,) in part_rows:
            part = _json(raw_part)
            if not isinstance(part, dict):
                raise ValueError(f"malformed OpenCode part in message {message_id}")
            event = _part_event(part, stamp)
            if not event:
                continue
            if event["type"] == "_text":
                message_text.append(event["text"])
            elif event["type"] == "_many":
                if include_events:
                    tool_events.extend(event["events"])
            elif include_events:
                tool_events.append(event)
        if message_text:
            text = "\n".join(message_text)
            if role == "user" and user_title is None:
                user_title = text.strip()[:160]
            if include_events and role in ("user", "assistant"):
                events.extend(tool_events)
                events.append({"type": "user_message" if role == "user" else "assistant_message", "text": text, "timestamp": stamp})
            elif include_events:
                events.extend(tool_events)
        elif include_events:
            events.extend(tool_events)
    return _make_summary(session, session.get("title") or "", user_title, first_time, last_time, events, include_events)


def _parse_legacy(connection: sqlite3.Connection, session: dict, include_events: bool) -> tuple[dict, list[dict], str]:
    """Read the official legacy message/part projection retained in v1 databases."""
    session_id = session["id"]
    rows = connection.execute(
        "SELECT id, time_created, data FROM message WHERE session_id = ? ORDER BY time_created, id", (session_id,)
    ).fetchall()
    title = session.get("title") or ""
    user_title = None
    first_time = last_time = None
    events = []
    for message_id, created, raw_data in rows:
        message = _json(raw_data)
        if not isinstance(message, dict):
            raise ValueError(f"malformed OpenCode message {message_id}")
        role = message.get("role")
        stamp = _iso(message.get("time", {}).get("created") if isinstance(message.get("time"), dict) else created) or _iso(created)
        first_time = min(filter(None, [first_time, stamp]), default=None)
        last_time = max(filter(None, [last_time, stamp]), default=None)
        if not include_events and (role != "user" or user_title is not None):
            continue
        part_rows = connection.execute(
            "SELECT data FROM part WHERE message_id = ? AND data LIKE '%\"type\": \"text\"%' ORDER BY time_created, id LIMIT 1", (message_id,)
        ).fetchall() if not include_events else connection.execute(
            "SELECT data FROM part WHERE message_id = ? ORDER BY time_created, id", (message_id,)
        ).fetchall()
        text_parts = []
        tool_events = []
        for (raw_part,) in part_rows:
            part = _json(raw_part)
            if not isinstance(part, dict):
                raise ValueError(f"malformed OpenCode part in message {message_id}")
            event = _part_event(part, stamp)
            if not event:
                continue
            if event["type"] == "_text":
                text_parts.append(event["text"])
            elif event["type"] == "_many":
                tool_events.extend(event["events"])
            else:
                tool_events.append(event)
        if text_parts:
            text = "\n".join(text_parts)
            if role == "user" and user_title is None:
                user_title = text.strip()[:160]
            if include_events and role in ("user", "assistant"):
                events.extend(tool_events)
                events.append({"type": "user_message" if role == "user" else "assistant_message", "text": text, "timestamp": stamp})
        elif include_events:
            events.extend(tool_events)
    return _make_summary(session, session.get("title") or "", user_title, first_time, last_time, events, include_events)


def _make_summary(session, title, user_title, first_time, last_time, events, include_events):
    if user_title:
        title = user_title
    started = _iso(session.get("time_created")) or first_time
    updated = _iso(session.get("time_updated")) or last_time or started
    if updated is None:
        updated = datetime.fromtimestamp(database_path().stat().st_mtime, timezone.utc).isoformat()
    if started is None:
        started = updated
    summary = {
        "id": f"opencode:{session['id']}", "tool": "opencode", "source": "opencode",
        "started": started, "updated": updated, "title": title,
        "cwd": session.get("directory") or "",
        "active": (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).total_seconds() <= 120,
    }
    digest = hashlib.sha256((json.dumps(session, sort_keys=True) + str(session.get("time_updated"))).encode()).hexdigest()
    events.sort(key=lambda event: (event.get("timestamp") or "", _EVENT_ORDER.get(event["type"], 9)))
    if len(events) > MAX_EVENTS:
        summary["truncated"] = True
        events = events[-MAX_EVENTS:]
    elif include_events:
        summary["truncated"] = False
    return summary, events if include_events else [], digest


def _parse(connection, session, include_events):
    table_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "session_message" in table_names:
        return _parse_v2(connection, session, include_events)
    if {"message", "part"} <= table_names:
        return _parse_legacy(connection, session, include_events)
    raise ValueError("database has no supported OpenCode message tables")


def _session_rows(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT id, title, directory, time_created, time_updated FROM session ORDER BY time_updated DESC"
    ).fetchall()
    keys = ("id", "title", "directory", "time_created", "time_updated")
    result = []
    for row in rows:
        session = dict(zip(keys, row))
        result.append(session)
    return result


def list_sessions() -> list[dict]:
    path = database_path()
    if not path.is_file():
        return []
    signature = _signature(path)
    if signature is None:
        return []
    with _CACHE_LOCK:
        if signature in _FILE_CACHE:
            return [dict(row) for row in _FILE_CACHE[signature]]
        for key in list(_FILE_CACHE):
            if key[0] == signature[0] and key != signature:
                _FILE_CACHE.pop(key, None)
    connection = None
    try:
        connection = _connect()
        connection.execute("PRAGMA query_only = ON")
        # Force SQLite to read the database now. A mere file signature may be
        # available even while another process holds an exclusive lock.
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "session" not in tables:
            raise ValueError("database has no OpenCode session table")
        summaries = []
        for session in _session_rows(connection):
            try:
                summary, _, _ = _parse(connection, session, include_events=False)
                summaries.append({key: summary[key] for key in ("id", "tool", "source", "started", "updated", "title", "cwd", "active")})
            except (ValueError, TypeError, sqlite3.Error) as exc:
                log.warning("Skipping malformed OpenCode session %s: %s", session.get("id"), exc)
        with _CACHE_LOCK:
            _FILE_CACHE[signature] = summaries
        return [dict(row) for row in summaries]
    except (sqlite3.Error, OSError, ValueError) as exc:
        with _CACHE_LOCK:
            _FILE_CACHE.pop(signature, None)
        _warning(exc)
        return []
    finally:
        if connection is not None:
            connection.close()


def read_session(session_id: str) -> tuple[dict, list[dict], str] | None:
    if not session_id.startswith("opencode:"):
        return None
    raw_id = session_id.removeprefix("opencode:")
    connection = None
    try:
        connection = _connect()
        connection.execute("PRAGMA query_only = ON")
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "session" not in tables:
            raise ValueError("database has no OpenCode session table")
        session = next((row for row in _session_rows(connection) if row["id"] == raw_id), None)
        if session is None:
            return None
        summary, events, digest = _parse(connection, session, include_events=True)
        return summary, events, digest
    except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
        _warning(exc)
        return None
    finally:
        if connection is not None:
            connection.close()
