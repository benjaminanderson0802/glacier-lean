"""Normalize Glacier chats, local harness sessions, and Build tasks into message threads."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone

import audit_log
import secrets_store
import session_mirror
import store
import teams
import vault

PAGE_SIZE = 50
MAX_TEXT = 20_000
_SOURCE_PREFIX = {"opencode": "opencode:", "claude": "claude-code:", "gemini": "gemini:"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe(value) -> str:
    try:
        return secrets_store.redact(str(value or ""))
    except Exception:
        return "[message hidden: secrets could not be checked]"


def _source(row: dict) -> str:
    source = row.get("source")
    if source in {"codex", "claude", "opencode", "gemini"}:
        return source
    tool = str(row.get("tool", "codex")).casefold()
    return tool if tool in {"codex", "claude", "opencode", "gemini"} else "codex"


def _session_id(source: str, raw_id: str) -> str:
    prefix = _SOURCE_PREFIX.get(source, "")
    return raw_id if prefix and raw_id.startswith(prefix) else prefix + raw_id if prefix else f"codex:{raw_id}"


def _raw_session_id(thread_id: str, source: str) -> str:
    if source == "codex" and thread_id.startswith("codex:"):
        return thread_id[len("codex:"):]
    prefix = _SOURCE_PREFIX.get(source)
    return thread_id[len(prefix):] if prefix and thread_id.startswith(prefix) else thread_id


def _claude_available() -> bool:
    binary = os.environ.get("GLACIER_CLAUDE_BIN") or "claude"
    return bool(shutil.which(binary) or (os.path.isfile(binary) and os.access(binary, os.X_OK)))


def _codex_available() -> bool:
    binary = os.environ.get("GLACIER_CODEX_BIN") or os.environ.get("CODEX_BIN") or "codex"
    return bool(shutil.which(binary) or (os.path.isfile(binary) and os.access(binary, os.X_OK)))


def _timestamp(value) -> str:
    if isinstance(value, str) and value:
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return stamp.astimezone(timezone.utc).isoformat(timespec="milliseconds")
        except ValueError:
            pass
    return ""


def _conversation_rows(query: str) -> list[dict]:
    from routes import assistant_chat

    result = []
    for row in assistant_chat._conversation_items(query):
        try:
            _, meta, messages = assistant_chat._conversation_note(row["id"])
        except Exception:
            continue
        last = messages[-1] if messages else {}
        result.append({"id": f"glacier:{row['id']}", "source": "glacier",
                       "title": _safe(row.get("title") or "Conversation"),
                       "last_text": _safe(last.get("text", "")), "last_at": _timestamp(row.get("updated") or meta.get("updated")),
                       "unread": False, "can_send": True})
    return result


def _session_rows(query: str) -> list[dict]:
    terms = [term.casefold() for term in re.findall(r"\w+", query) if term]
    result = []
    for row in session_mirror.list_sessions():
        source = _source(row)
        title = _safe(row.get("title") or source.title())
        session_id = _session_id(source, str(row.get("id", "")))
        # Session summaries are deliberately metadata-only; opening every transcript here would
        # turn the inbox refresh into a full scan of every large local session file.
        last_text = title
        if row.get("active"):
            found = session_mirror.read_session(str(row.get("id", "")))
            events = found[1] if found else []
            latest = next((event for event in reversed(events) if event.get("text")), None)
            if latest:
                last_text = _safe(latest["text"])
        searchable = f"{title} {source} {last_text}".casefold()
        if terms and not all(term in searchable for term in terms):
            # Detail is read only for a matching title; avoid loading every transcript on search.
            continue
        can_send = source == "codex" and _codex_available() or source == "claude" and _claude_available()
        result.append({"id": session_id, "source": source, "title": title,
                       "last_text": last_text, "last_at": _timestamp(row.get("updated")),
                       "unread": False, "can_send": bool(can_send)})
    return result


def _worker_rows(query: str) -> list[dict]:
    if not teams.DB:
        teams.init()
    result = []
    with teams._conn() as connection:
        rows = connection.execute("SELECT team_id,status,plan,state FROM glacier_teams ORDER BY created_at DESC").fetchall()
    terms = [term.casefold() for term in re.findall(r"\w+", query) if term]
    for row in rows:
        plan, state = json.loads(row["plan"]), json.loads(row["state"])
        tasks = {str(task.get("id")): task for task in plan.get("tasks", [])}
        for task_id, task in tasks.items():
            item = state.get("tasks", {}).get(task_id, {})
            notes = item.get("owner_notes", [])
            output = _safe(item.get("output", ""))
            latest = notes[-1].get("text", "") if notes else output or f"Task {item.get('status', 'pending')}"
            title = _safe(f"{task.get('title', task_id)} · {plan.get('vision', {}).get('goal', row['team_id'])}")
            searchable = f"{title} {output} {latest} {row['team_id']} {task_id}".casefold()
            if terms and not all(term in searchable for term in terms):
                continue
            result.append({"id": f"worker:{row['team_id']}:{task_id}", "source": "worker", "title": title,
                           "last_text": _safe(latest), "last_at": _timestamp(notes[-1].get("at")) if notes else "",
                           "unread": False, "can_send": row["status"] not in {"done", "stopped"}})
    return result


def list_threads(query: str = "") -> list[dict]:
    rows = _conversation_rows(query) + _session_rows(query) + _worker_rows(query)
    return sorted(rows, key=lambda row: row.get("last_at", ""), reverse=True)


def _message(mid: str, sender: str, author: str, text: str, at: str, kind: str = "text") -> dict:
    return {"id": mid, "from": sender, "author": author, "text": _safe(text), "at": _timestamp(at), "kind": kind}


def _glacier_messages(thread_id: str) -> list[dict] | None:
    if not thread_id.startswith("glacier:"):
        return None
    from routes import assistant_chat
    conversation_id = thread_id[len("glacier:"):]
    _, _, rows = assistant_chat._conversation_note(conversation_id)
    return [_message(f"{conversation_id}:{index}", "me" if row["who"] == "you" else "them",
                     "you" if row["who"] == "you" else "Glacier", row["text"], row["at"])
            for index, row in enumerate(rows)]


def _session_messages(thread_id: str) -> list[dict] | None:
    source = "codex" if thread_id.startswith("codex:") else next(
        (item for item, prefix in _SOURCE_PREFIX.items() if thread_id.startswith(prefix)), None)
    if not source:
        return None
    raw_id = _raw_session_id(thread_id, source)
    read_id = raw_id if source == "codex" else thread_id
    found = session_mirror.read_session(read_id)
    if not found:
        return None
    summary, events, _ = found
    source = _source(summary)
    result = []
    for index, event in enumerate(events):
        event_type = event.get("type", "other")
        sender = "me" if event_type == "user_message" else "them" if event_type == "assistant_message" else "system"
        kind = "text" if sender != "system" else "tool"
        author = "you" if sender == "me" else source.title() if sender == "them" else "tool"
        result.append(_message(f"{thread_id}:{index}", sender, author, event.get("text", ""),
                               event.get("timestamp") or event.get("at") or summary.get("updated"), kind))
    return result


def _worker_messages(thread_id: str) -> list[dict] | None:
    match = re.fullmatch(r"worker:([^:]+):(.+)", thread_id)
    if not match:
        return None
    team_id, task_id = match.groups()
    try:
        row = teams._read(team_id)
    except ValueError:
        return None
    task = row["state"].get("tasks", {}).get(task_id)
    if task is None:
        return None
    result = []
    output = task.get("output")
    if output:
        result.append(_message(f"{thread_id}:output", "them", task.get("role", "worker"), output,
                               task.get("updated_at") or row.get("created_at", "")))
    for index, note in enumerate(task.get("owner_notes", [])):
        result.append(_message(note.get("id", f"{thread_id}:owner:{index}"), "me", "you", note.get("text", ""), note.get("at", "")))
    log = str(row["state"].get("progress_log", ""))
    for index, line in enumerate(log.splitlines()):
        if task_id.casefold() in line.casefold():
            result.append(_message(f"{thread_id}:log:{index}", "system", "Glacier", line, row.get("created_at", ""), "status"))
    result.sort(key=lambda item: item["at"] or "", reverse=True)
    return result


def get_messages(thread_id: str, before: str | None = None, limit: int = PAGE_SIZE) -> list[dict] | None:
    if thread_id.startswith("glacier:"):
        rows = _glacier_messages(thread_id)
    elif thread_id.startswith(("codex:", *_SOURCE_PREFIX.values())):
        rows = _session_messages(thread_id)
    elif thread_id.startswith("worker:"):
        rows = _worker_messages(thread_id)
    else:
        rows = None
    if rows is None:
        return None
    rows.sort(key=lambda item: (item["at"] or "", item["id"]), reverse=True)
    if before:
        cursor = next((row for row in rows if row["id"] == before), None)
        if cursor:
            rows = [row for row in rows if (row["at"] or "", row["id"]) < (cursor["at"] or "", cursor["id"])]
        else:
            cutoff = _timestamp(before)
            rows = [row for row in rows if row["at"] and row["at"] < cutoff]
    return rows[:max(1, min(int(limit), PAGE_SIZE))]


def _append_worker_note(thread_id: str, text: str) -> dict:
    match = re.fullmatch(r"worker:([^:]+):(.+)", thread_id)
    if not match:
        raise ValueError("worker thread not found")
    team_id, task_id = match.groups()
    text = _safe(text)
    stamp, note_id = now(), str(uuid.uuid4())
    with teams._team_state_lock:
        with teams._conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT state,plan,status FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
            if not row:
                raise ValueError("worker thread not found")
            state = json.loads(row["state"])
            task = state.get("tasks", {}).get(task_id)
            if task is None:
                raise ValueError("worker task not found")
            note = {"id": note_id, "text": text, "at": stamp, "author": "owner"}
            task.setdefault("owner_notes", []).append(note)
            state["progress_log"] = (str(state.get("progress_log", "")).rstrip() +
                                      f"\nOwner instruction for {task_id}: {text}").strip()
            plan = json.loads(row["plan"])
            planned_task = next((item for item in plan.get("tasks", []) if str(item.get("id")) == task_id), None)
            if planned_task is not None:
                instructions = "\n".join(f"- {item['text']}" for item in task["owner_notes"])
                marker = "\n\nOwner instructions from Messages:\n"
                description = str(planned_task.get("description", ""))
                description = description.split(marker, 1)[0]
                planned_task["description"] = description + marker + instructions
            connection.execute("UPDATE glacier_teams SET state=?,plan=? WHERE team_id=?",
                               (json.dumps(state), json.dumps(plan), team_id))
    audit_log.record("team.owner_instruction", what={"team_id": team_id, "task_id": task_id, "message_id": note_id})
    message = _message(note_id, "me", "you", text, stamp)
    store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": message})
    return message


def _cli_binary(source: str) -> str:
    return (os.environ.get("GLACIER_CLAUDE_BIN") or "claude") if source == "claude" else (
        os.environ.get("GLACIER_CODEX_BIN") or os.environ.get("CODEX_BIN") or "codex")


def send_session(thread_id: str, source: str, text: str) -> dict:
    if source not in {"codex", "claude"}:
        raise PermissionError("This conversation is read-only")
    binary = _cli_binary(source)
    if not (shutil.which(binary) or os.path.isfile(binary) and os.access(binary, os.X_OK)):
        raise FileNotFoundError(f"{source.title()} CLI is not installed")
    raw_id = _raw_session_id(thread_id, source)
    if source == "claude":
        # Claude ids in the mirror are prefixed with claude-code:; resume takes the native session id.
        raw_id = raw_id.removeprefix("claude-code:")
        args = [binary, "--resume", raw_id, "-p", text]
    else:
        args = [binary, "exec", "resume", raw_id, text]
    owner_message = _message(f"{thread_id}:{uuid.uuid4()}", "me", "you", text, now())
    store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": owner_message})
    completed = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600, check=False)
    if completed.returncode:
        raise RuntimeError("The coding assistant could not continue this session.")
    reply = _safe(completed.stdout.strip())
    if not reply:
        reply = "The session continued without a text reply."
    message = _message(f"{thread_id}:{uuid.uuid4()}", "them", source.title(), reply, now())
    store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": message})
    return message


def create_session(source: str, text: str) -> tuple[dict, str]:
    if source not in {"codex", "claude"}:
        raise ValueError("Only Glacier, Codex, and Claude can start a new conversation")
    binary = _cli_binary(source)
    if not (shutil.which(binary) or os.path.isfile(binary) and os.access(binary, os.X_OK)):
        raise FileNotFoundError(f"{source.title()} CLI is not installed")
    args = [binary, "exec", "--json", text] if source == "codex" else [binary, "-p", text, "--output-format", "json"]
    completed = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600, check=False)
    if completed.returncode:
        raise RuntimeError("The coding assistant could not start a conversation.")
    native_id, reply = "", ""
    if source == "claude":
        try:
            payload = json.loads(completed.stdout)
            native_id = str(payload.get("session_id") or payload.get("sessionId") or "")
            reply = str(payload.get("result") or payload.get("text") or "")
        except ValueError:
            pass
    else:
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            native_id = str(event.get("session_id") or event.get("thread_id") or native_id)
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            native_id = str(payload.get("id") or payload.get("session_id") or native_id)
            if event.get("type") in {"item.completed", "response_item"}:
                item = event.get("item", payload)
                if isinstance(item, dict) and item.get("type") == "agent_message":
                    reply = str(item.get("text") or "")
                elif isinstance(item, dict) and item.get("role") == "assistant":
                    reply = str(item.get("content") or "")
    if not native_id:
        raise RuntimeError(f"{source.title()} did not return a resumable session id.")
    reply = _safe(reply or completed.stdout.strip())
    if not reply:
        reply = "The session started without a text reply."
    message = _message(f"{source}:{native_id}:{uuid.uuid4()}", "them", source.title(), reply, now())
    thread_id = _session_id(source, native_id)
    owner_message = _message(f"{thread_id}:{uuid.uuid4()}", "me", "you", text, now())
    store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": owner_message})
    store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": message})
    return message, native_id
