"""Build interview, reviewed team plans and team-run API."""
import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import teams
import vault
import audit_log

router = APIRouter()


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


@router.post("/api/build/interview")
def interview(turn: InterviewTurn):
    if turn.engine not in ("codex", "local"):
        raise HTTPException(400, "engine must be codex or local")
    import assistant
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
        answer = (assistant._ask_local if turn.engine == "local" else assistant._ask_codex)(prompt, {
            "type": "object", "additionalProperties": False, "required": ["reply", "automation"],
            "properties": {"reply": {"type": "string"}, "automation": {"type": "boolean"}}})
        assistant_chat._append_conversation(conversation_id, turn.message, answer["reply"])
        audit_log.record("build.interview_turn", what={"conversation_id": conversation_id, "engine": turn.engine})
        return {"conversation_id": conversation_id, "reply": answer["reply"],
                "conversation_path": assistant_chat._conversation_path(conversation_id)}
    except Exception as exc:
        raise HTTPException(502, f"the interviewer could not answer: {exc}") from exc


@router.post("/api/build/vision")
def confirm_vision(body: VisionBody):
    try:
        result = teams.create_vision(body.vision)
        audit_log.record("build.vision_confirmed", what={"path": result["path"]})
        return {"confirmed": True, **result}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/api/build/spec")
def confirm_spec(body: SpecBody):
    spec = body.spec
    if not isinstance(spec.get("requirements"), list) or not isinstance(spec.get("out_of_scope"), list) or not isinstance(spec.get("acceptance"), list) or not spec["acceptance"]:
        raise HTTPException(400, "Spec needs requirements, out_of_scope and end-to-end acceptance checks")
    audit_log.record("build.spec_approved", what={"requirements": len(spec["requirements"]),
                                                  "acceptance_checks": len(spec["acceptance"])})
    return {"approved": True, "spec": spec}


@router.post("/api/build/plan")
def propose_plan(body: PlanBody):
    try:
        vision = teams.read_vision(body.vision_path)
    except (OSError, ValueError, json.JSONDecodeError):
        raise HTTPException(400, "Vision note was not found or is not a structured Vision")
    try:
        plan = teams.plan_team(vision, body.engine)
        audit_log.record("build.plan_requested", what={"vision_path": body.vision_path, "engine": body.engine,
                                                        "roles": len(plan.get("team", {}).get("roles", [])),
                                                        "features": len(plan.get("features", []))})
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
        audit_log.record("team.plan_approved", what={"team_id": result["team_id"], "vision_path": body.vision_path,
                                                      "roles": len(body.plan.get("team", {}).get("roles", [])),
                                                      "tasks": len(body.plan.get("tasks", []))})
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


@router.post("/api/teams/{team_id}/run")
def run_team(team_id: str):
    try:
        started = teams.start(team_id)
        audit_log.record("team.run_started", what={"team_id": started})
        return {"team_id": started, "status": "running"}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/pause")
def pause_team(team_id: str):
    try:
        result = teams.pause(team_id)
        audit_log.record("team.pause_requested", what={"team_id": team_id, "status": result["status"]})
        return result
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/stop")
def stop_team(team_id: str):
    try:
        result = teams.stop(team_id)
        audit_log.record("team.stop_requested", what={"team_id": team_id, "status": result["status"]})
        return result
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/tasks/{task_id}/approve")
def approve_task(team_id: str, task_id: str, body: TaskApproval):
    try:
        result = teams.approval(team_id, task_id, body.approved)
        audit_log.record("team.task_approval", what={"team_id": team_id, "task_id": task_id,
                                                      "approved": body.approved})
        return result
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/api/teams/{team_id}/features/{feature_id}/grade")
def grade_feature(team_id: str, feature_id: str, body: FeatureGrade):
    try:
        result = teams.update_feature(team_id, feature_id, body.status, body.evidence, body.actor)
        audit_log.record("team.feature_graded", who=body.actor,
                         what={"team_id": team_id, "feature_id": feature_id, "status": body.status})
        return result
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc
