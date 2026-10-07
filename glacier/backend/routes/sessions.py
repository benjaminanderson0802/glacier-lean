"""Read-only API for local coding-agent session logs."""
import re

from fastapi import APIRouter, HTTPException

import secrets_store
import session_mirror
import vault

router = APIRouter()


@router.get("/api/sessions")
def sessions():
    rows = session_mirror.list_sessions()
    for row in rows:
        row["title"] = secrets_store.redact(row.get("title", ""))
        row["cwd"] = secrets_store.redact(row.get("cwd", ""))
    return rows


@router.get("/api/sessions/{session_id}")
def session(session_id: str):
    found = session_mirror.read_session(session_id)
    if not found:
        raise HTTPException(404, "Session not found")
    summary, events, _ = found
    for event in events:
        event["text"] = secrets_store.redact(event.get("text", ""))
    summary["title"] = secrets_store.redact(summary.get("title", ""))
    summary["cwd"] = secrets_store.redact(summary.get("cwd", ""))
    return {**summary, "events": events}


@router.post("/api/sessions/{session_id}/save-to-memory")
def save_to_memory(session_id: str):
    found = session_mirror.read_session(session_id)
    if not found:
        raise HTTPException(404, "Session not found")
    summary, events, version = found
    safe_id = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", session_id).strip(" .")[:64]
    if not safe_id or safe_id.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        safe_id = f"session-{safe_id or 'log'}"
    path = f"sessions/{safe_id}-{version[:16]}.md"
    try:
        vault.read_raw_note(path)
        return {"saved": False, "path": path}
    except FileNotFoundError:
        pass
    lines = [f"# {summary['title'] or 'Codex session'}", "", f"Session: {session_id}",
             f"Started: {summary['started'] or 'unknown'}", f"Working folder: {summary['cwd'] or 'unknown'}", "", "## Conversation"]
    for event in events:
        label = {"user_message": "User", "assistant_message": "Codex", "command": "Command",
                 "command_output": "Command output", "file_change": "File changes", "other": "Other"}.get(event["type"], "Other")
        lines.append(f"\n**{label}:** {event['text']}")
    body = secrets_store.redact("\n".join(lines))
    try:
        vault.write_note(path, body, author="glacier-mirror")
    except ValueError as exc:
        raise HTTPException(400, "This session could not be saved to memory") from exc
    return {"saved": True, "path": path}
