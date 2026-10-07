"""Conversational assistant API. Planning is review-only; saving requires explicit approval."""
import json
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import assistant
import vault

router = APIRouter()
_proposals: dict[str, dict] = {}


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ApplyRequest(BaseModel):
    approve: bool


def _event(name: str, **data) -> str:
    return "data: " + json.dumps({"type": name, **data}, ensure_ascii=False) + "\n\n"


def _chat_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["reply", "automation"],
            "properties": {"reply": {"type": "string"}, "automation": {"type": "boolean"}}}


def _ask(message: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        schema_path, output_path = os.path.join(directory, "schema.json"), os.path.join(directory, "answer.json")
        with open(schema_path, "w", encoding="utf-8") as schema_file:
            json.dump(_chat_schema(), schema_file)
        args = [os.environ.get("GLACIER_CHAT_BIN") or os.environ.get("CODEX_BIN", "codex"), "exec", "--json",
                "--skip-git-repo-check", "-s", "read-only", "-C", directory,
                "--output-schema", schema_path, "-o", output_path, "--", message]
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
        if result.returncode or not os.path.isfile(output_path):
            raise RuntimeError("The assistant could not answer. Please try again.")
        with open(output_path, encoding="utf-8") as output:
            answer = json.load(output)
    if not isinstance(answer.get("reply"), str) or not isinstance(answer.get("automation"), bool):
        raise ValueError("The assistant returned an invalid answer.")
    return answer


def _is_automation(message: str, model_answer: dict) -> bool:
    # The schema decision is model-led; common plain-language asks are also routed safely to planning.
    text = message.lower()
    return model_answer["automation"] or any(phrase in text for phrase in
        ("make me", "create an automation", "automate", "every day", "daily ", "each day", "every week", "weekly "))


def _conversation_path(conversation_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", conversation_id).strip("-")[:80] or "conversation"
    return f"conversations/{safe_id}.md"


def _append_conversation(conversation_id: str, user_message: str, answer: str) -> None:
    path = _conversation_path(conversation_id)
    try:
        previous = vault.read_note(path).rstrip()
    except FileNotFoundError:
        previous = f"# Conversation {conversation_id}\n"
    stamp = datetime.now(timezone.utc).isoformat()
    body = previous + f"\n\n## {stamp}\n\n**You:** {user_message}\n\n**Assistant:** {answer}\n"
    vault.write_note(path, body, agent="assistant")


@router.post("/api/assistant/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    def stream():
        run_id, message_id = str(uuid.uuid4()), str(uuid.uuid4())
        yield _event("RUN_STARTED", threadId=conversation_id, runId=run_id)
        try:
            answer = _ask(request.message)
            if _is_automation(request.message, answer):
                import app
                proposal_id = str(uuid.uuid4())
                flow_id = re.sub(r"[^a-z0-9]+", "-", request.message.lower()).strip("-")[:40] or "new-flow"
                plan = assistant.plan(request.message, app.NODE_CATALOG, flow_id)
                if plan.get("problems") or not plan.get("flow"):
                    raise RuntimeError("I could not make a valid plan yet. Please try changing the request.")
                proposal = {"id": proposal_id, "conversation_id": conversation_id, **plan}
                _proposals[proposal_id] = proposal
                _append_conversation(conversation_id, request.message,
                                     f"{plan['explanation']} Proposal {proposal_id} is ready for your review.")
                tool_id = str(uuid.uuid4())
                yield _event("TOOL_CALL_START", toolCallId=tool_id, toolCallName="propose_flow", messageId=message_id)
                yield _event("TOOL_CALL_ARGS", toolCallId=tool_id, delta=json.dumps(proposal, ensure_ascii=False))
                yield _event("TOOL_CALL_END", toolCallId=tool_id)
                reply = plan["explanation"]
            else:
                reply = answer["reply"]
                _append_conversation(conversation_id, request.message, reply)
            yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
            yield _event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=reply)
            yield _event("TEXT_MESSAGE_END", messageId=message_id)
            yield _event("RUN_FINISHED", threadId=conversation_id, runId=run_id)
        except Exception as error:
            message = str(error).strip() or "The assistant could not answer. Please try again."
            yield _event("RUN_ERROR", threadId=conversation_id, runId=run_id, message=message)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/api/assistant/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: str, request: ApplyRequest):
    proposal = _proposals.get(proposal_id)
    if proposal is None:
        from fastapi import HTTPException
        raise HTTPException(404, "proposal not found")
    if not request.approve:
        _proposals.pop(proposal_id, None)
        return {"discarded": True}
    import app
    import runner
    import verify
    flow = proposal["flow"]
    flow["id"] = flow.get("id") or "new-flow"
    flow.setdefault("name", flow["id"])
    flow.setdefault("nodes", [])
    flow.setdefault("edges", [])
    bad = [node.get("type") for node in flow["nodes"] if node.get("type") not in app.NODE_TYPES]
    if bad:
        from fastapi import HTTPException
        raise HTTPException(400, f"unknown node types: {bad}")
    try:
        verify.validate(flow.get("acceptance"))
    except ValueError as error:
        from fastapi import HTTPException
        raise HTTPException(400, str(error))
    try:
        path = runner.env_path(flow["id"])
        vault.safe_path(path)
        runner.sync_schedule(flow)
    except Exception as error:
        from fastapi import HTTPException
        raise HTTPException(400, str(error))

    # Keep the standard vault writer (and its assistant author/event/index behavior),
    # then tag the same commit so the existing run-undo route can find it by conversation.
    commit = vault.write_note(path, json.dumps(flow, indent=2), agent="assistant")
    conversation_id = proposal["conversation_id"]
    vault._repo.git.commit("--amend", "-m", f"[run:{conversation_id}] assistant approved proposal")
    commit = vault._repo.head.commit.hexsha[:8]
    result = {"saved": True, "commit": commit}
    _proposals.pop(proposal_id, None)
    _append_conversation(proposal["conversation_id"], "Approved proposal", f"Saved flow {proposal['flow']['name']}.")
    return result
