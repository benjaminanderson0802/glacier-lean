"""Read-only API for local coding-agent session logs."""
from fastapi import APIRouter, HTTPException

import secrets_store
import session_mirror
import vault

router = APIRouter()


@router.get("/api/sessions")
def sessions():
    return session_mirror.list_sessions()


@router.get("/api/sessions/{session_id}")
def session(session_id: str):
    found = session_mirror.read_session(session_id)
    if not found:
        raise HTTPException(404, "Session not found")
    summary, events, _ = found
    return {**summary, "events": events}


@router.post("/api/sessions/{session_id}/save-to-memory")
def save_to_memory(session_id: str):
    found = session_mirror.read_session(session_id)
    if not found:
        raise HTTPException(404, "Session not found")
    summary, events, version = found
    safe_id = session_id.replace("/", "-").replace("\\", "-")[:80]
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
