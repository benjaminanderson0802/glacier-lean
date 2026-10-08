"""Assistant API: propose a flow from a plain-language goal. Proposals are never saved or run here."""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import assistant
import audit_log

router = APIRouter()


class Goal(BaseModel):
    goal: str
    engine: str = "codex"
    flow_id: str = ""


@router.post("/api/assistant/plan")
def propose(g: Goal):
    import app  # the live catalog (core + plug-ins)
    fid = g.flow_id or (re.sub(r"[^a-z0-9]+", "-", g.goal.lower()).strip("-")[:40] or "new-flow")
    if g.engine not in ("codex", "claude", "gemini", "openai", "anthropic", "local"):
        raise HTTPException(400, "Choose an available Ask engine")
    try:
        import ask_context
        import secrets_store
        context = ask_context.build(g.goal, engine=g.engine,
                                    model=ask_context._settings().get("local_model") if g.engine == "local" else None)
        result = assistant.plan(secrets_store.redact(g.goal), app.NODE_CATALOG, fid, g.engine,
                                context=f"Shared context pack:\n{context}\n\nCurrent goal:\n")
        audit_log.record("assistant.plan_requested", what={"flow_id": fid, "engine": g.engine})
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"the planner could not make a plan: {e}")
