from fastapi import APIRouter, HTTPException

import rollback

router = APIRouter()


@router.get("/api/runs/{run_id}/changes")
def get_run_changes(run_id: str):
    return rollback.changes(run_id)


@router.post("/api/runs/{run_id}/undo")
def undo_run(run_id: str):
    try:
        return rollback.undo(run_id)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(409, f"Undo could not be completed: {exc}")


@router.post("/api/environments/{env_id}/restore")
def restore_environment(env_id: str, body: dict):
    commit = body.get("commit")
    if not isinstance(commit, str) or not commit:
        raise HTTPException(400, "Choose a saved version to restore.")
    try:
        new_commit = rollback.restore_flow(env_id, commit)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Flow could not be restored: {exc}")
    return {"restored": True, "new_commit": new_commit}
