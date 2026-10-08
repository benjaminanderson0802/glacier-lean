"""HTTP routes for rebuilding and reading generated flow status notes."""
from fastapi import APIRouter, HTTPException

import status_notes
import vault
import audit_log

router = APIRouter()


@router.post("/api/status/rebuild")
def rebuild_status():
    result = status_notes.write_all()
    audit_log.record("status.rebuilt", what={"written": result})
    return {"written": result}


@router.get("/api/status/{env_id}")
def get_status(env_id: str):
    if not env_id or "/" in env_id or "\\" in env_id or env_id in (".", ".."):
        raise HTTPException(400, "Choose a valid flow.")
    path = f"status/{env_id}.md"
    try:
        return {"markdown": vault.read_note(path)}
    except (FileNotFoundError, IsADirectoryError):
        # Render from current recorded data without writing when a rebuild has not run yet.
        if status_notes._db_path():
            return {"markdown": status_notes.render_flow(env_id)}
        raise HTTPException(404, f"status for {env_id} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
