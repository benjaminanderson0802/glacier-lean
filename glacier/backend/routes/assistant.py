"""Assistant API: propose a flow from a plain-language goal. Proposals are never saved or run here."""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import assistant

router = APIRouter()


class Goal(BaseModel):
    goal: str
    engine: str = "codex"
    flow_id: str = ""


@router.post("/api/assistant/plan")
def propose(g: Goal):
    import app  # the live catalog (core + plug-ins)
    fid = g.flow_id or (re.sub(r"[^a-z0-9]+", "-", g.goal.lower()).strip("-")[:40] or "new-flow")
    if g.engine not in ("codex", "local"):
        raise HTTPException(400, "engine must be codex or local")
    try:
        return assistant.plan(g.goal, app.NODE_CATALOG, fid, g.engine)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"the planner could not make a plan: {e}")
