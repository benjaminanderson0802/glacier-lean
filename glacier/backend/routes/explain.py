"""HTTP route for plain-language run explanations."""
from fastapi import APIRouter, HTTPException

import run_explain

router = APIRouter()


@router.get("/api/runs/{run_id}/explain")
def explain(run_id: str):
    result = run_explain.explain_run(run_id)
    if result is None:
        raise HTTPException(404, f"run {run_id} not found")
    return result
