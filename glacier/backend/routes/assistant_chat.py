"""Conversational assistant API. Planning is review-only; saving requires explicit approval."""
import json
import os
import re
import subprocess
import tempfile
import threading
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import assistant
import vault
import secrets_store
import logging
import git

router = APIRouter()
_proposals: dict[str, dict] = {}
_proposals_lock = threading.Lock()
MAX_PROPOSALS = 100


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
    body = previous + f"\n\n## {stamp}\n\n**You:** {secrets_store.redact(user_message)}\n\n**Assistant:** {secrets_store.redact(answer)}\n"
    vault.write_note(path, body, agent="assistant")


@router.post("/api/assistant/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", conversation_id):
        from fastapi import HTTPException
        raise HTTPException(400, "conversation_id must be a UUID")

    def stream():
        run_id, message_id = str(uuid.uuid4()), str(uuid.uuid4())
        yield _event("RUN_STARTED", threadId=conversation_id, runId=run_id)
        try:
            answer = _ask(request.message)
            automation = _is_automation(request.message, answer)
            if automation:
                import app
                proposal_id = str(uuid.uuid4())
                flow_id = re.sub(r"[^a-z0-9]+", "-", request.message.lower()).strip("-")[:40] or "new-flow"
                plan = assistant.plan(request.message, app.NODE_CATALOG, flow_id)
                if plan.get("problems") or not plan.get("flow"):
                    raise RuntimeError("I could not make a valid plan yet. Please try changing the request.")
                proposal = {"id": proposal_id, "conversation_id": conversation_id, **plan}
                with _proposals_lock:
                    _proposals[proposal_id] = proposal
                    while len(_proposals) > MAX_PROPOSALS:
                        _proposals.pop(next(iter(_proposals)))
                _append_conversation(conversation_id, request.message,
                                     f"{plan['explanation']} Proposal {proposal_id} is ready for your review.")
                tool_id = str(uuid.uuid4())
                yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
                yield _event("TOOL_CALL_START", toolCallId=tool_id, toolCallName="propose_flow", parentMessageId=message_id)
                yield _event("TOOL_CALL_ARGS", toolCallId=tool_id, delta=json.dumps(proposal, ensure_ascii=False))
                yield _event("TOOL_CALL_END", toolCallId=tool_id)
                reply = plan["explanation"]
            else:
                reply = answer["reply"]
                _append_conversation(conversation_id, request.message, reply)
            if not automation:
                yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
            if reply:
                yield _event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=reply)
            yield _event("TEXT_MESSAGE_END", messageId=message_id)
            yield _event("RUN_FINISHED", threadId=conversation_id, runId=run_id)
        except Exception as error:
            logging.getLogger(__name__).exception("Assistant chat failed")
            message = ("The assistant isn't installed" if isinstance(error, FileNotFoundError) else
                       "The assistant took too long" if isinstance(error, subprocess.TimeoutExpired) else
                       "The assistant could not answer. Please try again.")
            yield _event("RUN_ERROR", threadId=conversation_id, runId=run_id, message=message)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/api/assistant/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: str, request: ApplyRequest):
    with _proposals_lock:
        proposal = _proposals.get(proposal_id)
    if proposal is None:
        from fastapi import HTTPException
        raise HTTPException(404, "proposal not found")
    if not request.approve:
        with _proposals_lock:
            _proposals.pop(proposal_id, None)
        return {"discarded": True}
    import app
    import runner
    flow = proposal["flow"]
    flow["id"] = flow.get("id") or "new-flow"
    flow.setdefault("name", flow["id"])
    flow.setdefault("nodes", [])
    flow.setdefault("edges", [])
    try:
        path = runner.env_path(flow["id"])
        vault.safe_path(path)
    except Exception as error:
        from fastapi import HTTPException
        raise HTTPException(400, str(error))

    if flow.get("goal") and not flow.get("acceptance"):
        from fastapi import HTTPException
        raise HTTPException(400, "This goal has no check yet. Add a way to check it is done before running it.")
    run_id = str(uuid.uuid4())
    body = json.dumps(flow, indent=2)
    full_path = vault.safe_path(path)
    # Vault Git lock precedes any workspace merge lock held by runtime paths.
    with vault._lock:
        if os.path.exists(full_path):
            from fastapi import HTTPException
            raise HTTPException(409, "A flow with this name already exists")
        app.validate_environment(flow["id"], flow)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(dir=os.path.dirname(full_path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, full_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        vault._repo.index.add([os.path.relpath(full_path, vault.VAULT)])
        actor = git.Actor("assistant", "assistant@glacier.local")
        commit_obj = vault._repo.index.commit(
            f"[run:{run_id}] assistant applied proposal {proposal_id} conversation {proposal['conversation_id']}",
            author=actor, committer=actor)
        commit = commit_obj.hexsha[:8]
        db = vault._db()
        try:
            db.execute("DELETE FROM fts WHERE path=?", (path,))
            db.execute("INSERT INTO fts VALUES (?,?)", (path, body))
            db.execute("DELETE FROM links WHERE src=?", (path,))
            import re as _re
            for target in _re.findall(r"\[\[([^\]]+)\]\]", body):
                db.execute("INSERT INTO links VALUES (?,?)", (path, target.split("|", 1)[0].strip().removesuffix(".md")))
            db.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)",
                       ("assistant", "write_note", json.dumps({"path": path, "commit": commit})))
            db.commit()
        finally:
            db.close()
        try:
            import store
            store.broadcaster.publish({"type": "memory", "path": path, "change": "created",
                                       "author": "assistant", "run_id": run_id})
        except (ImportError, AttributeError):
            pass
    result = {"saved": True, "commit": commit, "undo_id": run_id}
    with _proposals_lock:
        _proposals.pop(proposal_id, None)
    proposal["run_id"] = run_id
    _append_conversation(proposal["conversation_id"], "Approved proposal", f"Saved flow {proposal['flow']['name']}.")
    return result
