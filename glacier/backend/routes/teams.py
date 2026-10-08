"""Build interview, reviewed team plans and team-run API."""
import json
import time
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import teams
import vault

router = APIRouter()
_delete_undo: dict[str, tuple[float, str, dict]] = {}


class InterviewTurn(BaseModel):
    conversation_id: str | None = None
    message: str
    engine: str = "codex"


class VisionBody(BaseModel):
    vision: dict


class SpecBody(BaseModel):
    spec: dict


class PlanBody(BaseModel):
    vision_path: str
    engine: str = "codex"


class ApprovePlan(BaseModel):
    plan: dict
    vision_path: str
    workspace: str | None = None


class TaskApproval(BaseModel):
    approved: bool


class FeatureGrade(BaseModel):
    status: str
    evidence: str
    actor: str


class DeleteUndo(BaseModel):
    undo_id: str


@router.post("/api/build/interview")
def interview(turn: InterviewTurn):
    if turn.engine not in teams.ASK_ENGINES:
        raise HTTPException(400, "Choose one of the available Ask engines.")
    from routes import assistant_chat
    conversation_id = turn.conversation_id or str(uuid.uuid4())
    try:
        conversation_id = assistant_chat._conversation_id(conversation_id)
    except HTTPException:
        raise
    prompt = ("Interview the owner about a project vision. Ask focused follow-up questions about goal, audience, "
              "done list, must-haves/must-nots, constraints, examples, and risks. Use the earlier conversation. "
              "Do not plan a team yet.\n" + assistant_chat._with_conversation_context(
                  turn.message, assistant_chat._conversation_context(conversation_id)))
    try:
        answer = teams.ask_engine(prompt, turn.engine, {
            "type": "object", "additionalProperties": False, "required": ["reply", "automation"],
            "properties": {"reply": {"type": "string"}, "automation": {"type": "boolean"}}})
        assistant_chat._append_conversation(conversation_id, turn.message, answer["reply"])
        return {"conversation_id": conversation_id, "reply": answer["reply"],
                "conversation_path": assistant_chat._conversation_path(conversation_id)}
    except Exception as exc:
        raise HTTPException(502, f"the interviewer could not answer: {exc}") from exc


@router.post("/api/build/vision")
def confirm_vision(body: VisionBody):
    try:
        return {"confirmed": True, **teams.create_vision(body.vision)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/build/spec")
def confirm_spec(body: SpecBody):
    spec = body.spec
    if not isinstance(spec.get("requirements"), list) or not isinstance(spec.get("out_of_scope"), list) or not isinstance(spec.get("acceptance"), list) or not spec["acceptance"]:
        raise HTTPException(400, "Spec needs requirements, out_of_scope and end-to-end acceptance checks")
    return {"approved": True, "spec": spec}


@router.post("/api/build/plan")
def propose_plan(body: PlanBody):
    try:
        vision = teams.read_vision(body.vision_path)
    except (OSError, ValueError, json.JSONDecodeError):
        raise HTTPException(400, "Vision note was not found or is not a structured Vision")
    try:
        plan = teams.plan_team(vision, body.engine)
        return {"plan": plan, "approved": False}
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"the planner could not make a team plan: {exc}") from exc


@router.post("/api/teams")
def approve_plan(body: ApprovePlan):
    try:
        result = teams.save_plan(body.plan, body.vision_path, body.workspace)
        result["approved"] = True
        return result
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/teams")
def list_teams():
    return teams.summary()


@router.get("/api/teams/{team_id}")
def get_team(team_id: str):
    try:
        return teams.get(team_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/api/teams/{team_id}/pause")
def pause_team(team_id: str):
    return teams.control(team_id, "pause")


@router.post("/api/teams/{team_id}/resume")
def resume_team(team_id: str):
    return teams.control(team_id, "resume")


@router.post("/api/teams/{team_id}/stop")
def stop_team(team_id: str):
    return teams.control(team_id, "stop")


@router.delete("/api/teams/{team_id}")
def delete_team(team_id: str):
    try:
        saved = teams.remove(team_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    undo_id = uuid.uuid4().hex
    _delete_undo[undo_id] = (time.time() + 30, "team", saved)
    return {"deleted": True, "undo_id": undo_id}


@router.delete("/api/build/interviews/{conversation_id}")
def delete_interview(conversation_id: str):
    from routes import assistant_chat
    conversation_id = assistant_chat._conversation_id(conversation_id)
    path = assistant_chat._conversation_path(conversation_id)
    try:
        body = vault.read_note(path)
    except (OSError, ValueError):
        raise HTTPException(404, "interview not found")
    import memory_hygiene
    memory_hygiene._commit_changes({}, [path], agent="owner")
    undo_id = uuid.uuid4().hex
    _delete_undo[undo_id] = (time.time() + 30, "note", {"path": path, "body": body})
    return {"deleted": True, "undo_id": undo_id}


@router.post("/api/build/undo-delete")
def undo_delete(body: DeleteUndo):
    item = _delete_undo.pop(body.undo_id, None)
    if not item or item[0] < time.time():
        raise HTTPException(404, "undo window expired")
    _, kind, saved = item
    if kind == "team": teams.restore(saved)
    else: vault.write_note(saved["path"], saved["body"], author="owner")
    return {"restored": True}


@router.post("/api/teams/{team_id}/run")
def run_team(team_id: str):
    try:
        return {"team_id": teams.start(team_id), "status": "running"}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/tasks/{task_id}/approve")
def approve_task(team_id: str, task_id: str, body: TaskApproval):
    try:
        return teams.approval(team_id, task_id, body.approved)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/features/{feature_id}/grade")
def grade_feature(team_id: str, feature_id: str, body: FeatureGrade):
    try:
        return teams.update_feature(team_id, feature_id, body.status, body.evidence, body.actor)
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc
