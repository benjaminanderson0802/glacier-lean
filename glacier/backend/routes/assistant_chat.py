"""Conversational assistant API. Planning is review-only; saving requires explicit approval."""
import json
import os
import re
import subprocess
import tempfile
import threading
import uuid
import shutil
import urllib.request
import urllib.error
from datetime import datetime, timezone
from egress import open_model_request

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import shell_commands
from pydantic import BaseModel

import assistant
import vault
import secrets_store
import logging
import git
from difflib import SequenceMatcher

router = APIRouter()
_proposals: dict[str, dict] = {}
_proposals_lock = threading.Lock()
MAX_PROPOSALS = 100


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ApplyRequest(BaseModel):
    approve: bool
    run_now: bool = False


def _conversation_id(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        raise HTTPException(400, "conversation_id must be a UUID")
    return value


def _conversation_messages(note: str) -> list[dict]:
    """Read only known timestamp sections and speaker labels from an editable note."""
    frontmatter = re.match(r"\A---\s*\n.*?\n---\s*\n?", note, re.S)
    body = note[frontmatter.end():] if frontmatter else note
    sections: list[tuple[str, list[str]]] = []
    current_at: str | None = None
    current_lines: list[str] = []

    def finish() -> None:
        if current_at is not None:
            sections.append((current_at, current_lines.copy()))

    for line in body.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if heading:
            finish()
            current_lines = []
            candidate = heading.group(1).strip()
            try:
                datetime.fromisoformat(candidate.replace("Z", "+00:00"))
                current_at = candidate
            except ValueError:
                current_at = None
            continue
        if current_at is not None:
            current_lines.append(line)
    finish()

    messages: list[dict] = []
    for at, lines in sections:
        who: str | None = None
        content: list[str] = []

        def emit() -> None:
            if who is not None:
                text = "\n".join(content).strip()
                if text:
                    messages.append({"who": who, "text": text, "at": at})

        for line in lines:
            speaker = re.match(r"^\*\*(You|Assistant):\*\*\s*(.*)$", line, re.I)
            if speaker:
                emit()
                who = "you" if speaker.group(1).casefold() == "you" else "glacier"
                content = [speaker.group(2)]
            elif who is not None:
                content.append(line)
        emit()
    return messages


def _conversation_title(conversation_id: str, meta: dict, messages: list[dict]) -> str:
    saved = str(meta.get("title", "")).strip()
    if saved and saved != f"Conversation {conversation_id}":
        return saved
    first_question = next((message["text"] for message in messages if message["who"] == "you"), "")
    one_line = " ".join(first_question.split())
    return one_line[:60].rstrip() or "Untitled conversation"


def _conversation_note(conversation_id: str) -> tuple[str, dict, list[dict]]:
    path = _conversation_path(conversation_id)
    try:
        note = vault.read_raw_note(path)
        meta, _ = vault.read_note_metadata(path)
    except (FileNotFoundError, OSError, UnicodeError, ValueError):
        raise HTTPException(404, "Conversation not found")
    messages = _conversation_messages(note)
    return path, meta, messages


def _conversation_items(q: str = "") -> list[dict]:
    items = []
    words = [word.casefold() for word in re.findall(r"\w+", q) if word]
    for path in vault.list_notes(".md", "conversations"):
        conversation_id = os.path.basename(path)[:-3]
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", conversation_id):
            continue
        try:
            _, meta, messages = _conversation_note(conversation_id)
        except HTTPException:
            continue
        title = _conversation_title(conversation_id, meta, messages)
        searchable = " ".join([title, *(item["text"] for item in messages)]).casefold()
        if words and not all(word in searchable for word in words):
            continue
        updated_values = [str(meta.get("updated", "")), *(item["at"] for item in messages)]
        dated = []
        for value in updated_values:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                dated.append((parsed, value))
            except (ValueError, TypeError):
                continue
        updated = max(dated, key=lambda entry: entry[0])[1] if dated else ""
        if not updated:
            try:
                updated = datetime.fromtimestamp(os.path.getmtime(vault.safe_path(path)), timezone.utc).isoformat()
            except OSError:
                updated = ""
        items.append({"id": conversation_id, "title": title, "updated": updated, "messages": len(messages)})
    return sorted(items, key=lambda item: item["updated"], reverse=True)


class RenameRequest(BaseModel):
    title: object = None
    model_config = {"extra": "forbid"}


def _event(name: str, **data) -> str:
    return "data: " + json.dumps({"type": name, **data}, ensure_ascii=False) + "\n\n"


def _chat_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["reply", "automation"],
            "properties": {"reply": {"type": "string"}, "automation": {"type": "boolean"}}}


def _codex_signed_in() -> bool:
    """Check Codex login state without reading or logging its output."""
    override = os.environ.get("GLACIER_CHAT_BIN") or os.environ.get("CODEX_BIN")
    binary = override or "codex"
    # An explicitly configured chat executable is an operator-selected harness. Some wrappers
    # do not implement Codex's login-status command, so let the selected executable report auth
    # problems when it is actually used.
    if override:
        return True
    try:
        args = shell_commands.executable_invocation(binary, "login", "status")
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _ollama_answers() -> bool:
    """Probe the local Ollama chat endpoint with a tiny non-generative tags request."""
    url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/tags"
    try:
        with open_model_request(url, timeout=1) as response:
            payload = json.loads(response.read())
        return bool(payload.get("models"))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def ask_route() -> tuple[str | None, str]:
    """Return the route Ask would use now and a plain reason for Settings."""
    configured = os.environ.get("GLACIER_ASK_ROUTE", "auto").strip().lower()
    codex = (os.environ.get("GLACIER_CHAT_BIN") or os.environ.get("CODEX_BIN") or "codex")
    if configured not in {"", "auto"}:
        if configured in {"local", "codex"}:
            return configured, f"Ask is set to use {configured.title()} directly."
        configured = "auto"
    # A configured chat program given as a full path counts as found even when Windows would not
    # treat its file type as runnable on its own (shell_commands handles running it).
    found = shutil.which(codex) or (os.path.isabs(codex) and os.path.isfile(codex))
    if found and _codex_signed_in():
        return "codex", "Codex is installed and signed in."
    if _ollama_answers():
        return "local", "Codex is unavailable or signed out, so Ask will use Ollama on this computer."
    return None, "Neither Codex sign-in nor a local Ollama model is available. Install Ollama with a model or sign in to Codex."


def _ask_codex(message: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        schema_path, output_path = os.path.join(directory, "schema.json"), os.path.join(directory, "answer.json")
        with open(schema_path, "w", encoding="utf-8") as schema_file:
            json.dump(_chat_schema(), schema_file)
        args = shell_commands.executable_invocation(os.environ.get("GLACIER_CHAT_BIN") or os.environ.get("CODEX_BIN", "codex"), "exec", "--json",
                "--skip-git-repo-check", "-s", "read-only", "-C", directory,
                "--output-schema", schema_path, "-o", output_path, "--", message)
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
        if result.returncode or not os.path.isfile(output_path):
            raise RuntimeError("The assistant could not answer. Please try again.")
        with open(output_path, encoding="utf-8") as output:
            answer = json.load(output)
    if not isinstance(answer.get("reply"), str) or not isinstance(answer.get("automation"), bool):
        raise ValueError("The assistant returned an invalid answer.")
    return answer


def _ask_local(message: str) -> dict:
    import urllib.request
    url = os.environ.get("GLACIER_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/chat"
    body = {"model": __import__("system_check").default_local_model(), "stream": False, "think": False,
            "format": _chat_schema(), "options": {"temperature": 0},
            "messages": [{"role": "user", "content": message}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with open_model_request(req, timeout=600) as response:
        answer = json.loads(json.loads(response.read())["message"]["content"])
    if not isinstance(answer, dict) or not isinstance(answer.get("reply"), str) or not isinstance(answer.get("automation"), bool):
        raise ValueError("The assistant returned an invalid answer.")
    return answer


def _ask(message: str, route: str) -> dict:
    return _ask_local(message) if route == "local" else _ask_codex(message)


def _existing_run_request(message: str) -> str | None:
    match = re.fullmatch(r"\s*run\s+my\s+(.+?)\s+now[.!?\s]*", message, re.I)
    return match.group(1).strip() if match else None


def _match_automation(name: str) -> tuple[list[dict], bool]:
    import vault
    candidates = []
    for path in vault.list_notes(".json", "environments"):
        try:
            flow = json.loads(vault.read_note(path))
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(flow, dict) or not flow.get("id") or not flow.get("name"):
            continue
        candidates.append(flow)
    exact = [flow for flow in candidates if str(flow["name"]).casefold() == name.casefold()]
    if exact:
        return exact, False
    ranked = sorted(((SequenceMatcher(None, name.casefold(), str(flow["name"]).casefold()).ratio(), flow)
                     for flow in candidates), key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.55:
        return [], False
    top_score = ranked[0][0]
    return [flow for score, flow in ranked if score >= 0.45 and top_score - score < 0.2][:5], True


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


@router.get("/api/assistant/conversations")
def list_conversations(q: str = ""):
    return _conversation_items(q)


@router.get("/api/assistant/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    conversation_id = _conversation_id(conversation_id)
    _, meta, messages = _conversation_note(conversation_id)
    return {"id": conversation_id, "title": _conversation_title(conversation_id, meta, messages), "messages": messages}


@router.get("/api/assistant/conversations/{conversation_id}/runs")
def conversation_runs(conversation_id: str):
    conversation_id = _conversation_id(conversation_id)
    _conversation_note(conversation_id)
    import store
    rows = []
    for item in store.list_runs(None):
        try:
            graph = store.graph_of(item["run_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if graph.get("_assistant_conversation_id") == conversation_id:
            rows.append({**item, "name": graph.get("name") or item["env_id"]})
    return rows


@router.post("/api/assistant/conversations/{conversation_id}/rename")
def rename_conversation(conversation_id: str, request: RenameRequest):
    conversation_id = _conversation_id(conversation_id)
    if not isinstance(request.title, str):
        raise HTTPException(400, "Title must be 1 to 80 characters with no line breaks")
    title = request.title.strip()
    if not 1 <= len(title) <= 80 or "\n" in title or "\r" in title:
        raise HTTPException(400, "Title must be 1 to 80 characters with no line breaks")
    path, _, _ = _conversation_note(conversation_id)
    raw = vault.read_raw_note(path)
    frontmatter = re.match(r"\A---\s*\n.*?\n---\s*\n?", raw, re.S)
    prefix = raw[:frontmatter.end()] if frontmatter else ""
    body = raw[frontmatter.end():] if frontmatter else raw
    heading = re.search(r"(?m)^#\s+.+$", body)
    if heading:
        body = body[:heading.start()] + "# " + title + body[heading.end():]
    else:
        body = "# " + title + "\n\n" + body
    commit = vault.write_note(path, prefix + body, author="owner")
    return {"id": conversation_id, "title": title, "commit": commit}


@router.post("/api/assistant/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", conversation_id):
        from fastapi import HTTPException
        raise HTTPException(400, "conversation_id must be a UUID")

    def stream():
        run_id, message_id = str(uuid.uuid4()), str(uuid.uuid4())
        yield _event("RUN_STARTED", threadId=conversation_id, runId=run_id)
        route, automation = None, False
        try:
            existing_name = _existing_run_request(request.message)
            if existing_name:
                matches, fuzzy = _match_automation(existing_name)
                if len(matches) != 1 or fuzzy:
                    if matches:
                        choices = ", ".join(flow["name"] for flow in matches)
                        reply = f"I found a few automations that may match: {choices}. Which one should I run?"
                    else:
                        reply = f"I could not find an automation named {existing_name}. Check its name and try again."
                    _append_conversation(conversation_id, request.message, reply)
                    yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
                    yield _event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=reply)
                    yield _event("TEXT_MESSAGE_END", messageId=message_id)
                    yield _event("RUN_FINISHED", threadId=conversation_id, runId=run_id)
                    return
                flow = matches[0]
                proposal_id = str(uuid.uuid4())
                proposal = {"id": proposal_id, "conversation_id": conversation_id, "run_existing": True,
                            "flow": {"id": flow["id"], "name": flow["name"]},
                            "explanation": f"Run {flow['name']} now?"}
                with _proposals_lock:
                    _proposals[proposal_id] = proposal
                _append_conversation(conversation_id, request.message, proposal["explanation"])
                tool_id = str(uuid.uuid4())
                yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
                yield _event("TOOL_CALL_START", toolCallId=tool_id, toolCallName="propose_run", parentMessageId=message_id)
                yield _event("TOOL_CALL_ARGS", toolCallId=tool_id, delta=json.dumps(proposal, ensure_ascii=False))
                yield _event("TOOL_CALL_END", toolCallId=tool_id)
                yield _event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=proposal["explanation"])
                yield _event("TEXT_MESSAGE_END", messageId=message_id)
                yield _event("RUN_FINISHED", threadId=conversation_id, runId=run_id)
                return
            route, reason = ask_route()
            if route is None:
                yield _event("TEXT_MESSAGE_START", messageId=message_id, role="assistant")
                yield _event("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=reason)
                yield _event("TEXT_MESSAGE_END", messageId=message_id)
                yield _event("RUN_FINISHED", threadId=conversation_id, runId=run_id)
                return
            answer = _ask(request.message, route)
            automation = _is_automation(request.message, answer)
            if automation:
                import app
                proposal_id = str(uuid.uuid4())
                flow_id = re.sub(r"[^a-z0-9]+", "-", request.message.lower()).strip("-")[:40] or "new-flow"
                plan = assistant.plan(request.message, app.NODE_CATALOG, flow_id, engine=route)
                if plan.get("problems") or not plan.get("flow"):
                    raise ValueError("The assistant could not make a valid plan.")
                if not isinstance(plan["flow"].get("acceptance"), list) or not plan["flow"]["acceptance"]:
                    raise ValueError("The assistant returned a plan without an acceptance check.")
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
            local_automation = route == "local" and (automation or any(phrase in request.message.lower() for phrase in
                ("make me", "create an automation", "automate", "every day", "daily ", "each day", "every week", "weekly ")))
            message = ("I could not turn that into an automation. Try rephrasing your request." if local_automation else
                       "Neither Codex nor a local model is available. Install Ollama with a model or sign in to Codex." if isinstance(error, (FileNotFoundError, ConnectionError, urllib.error.URLError)) else
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
    if proposal.get("run_existing"):
        if not request.run_now:
            from fastapi import HTTPException
            raise HTTPException(400, "Confirm that you want to run this automation")
        import runner
        flow = proposal["flow"]
        run_id = runner.start_run(flow["id"], {"_author": "assistant", "_assistant_conversation_id": proposal["conversation_id"]})
        with _proposals_lock:
            _proposals.pop(proposal_id, None)
        _append_conversation(proposal["conversation_id"], "Approved run", f"Started {flow['name']}.")
        return {"saved": False, "run_id": run_id, "status": "running"}
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
    _append_conversation(proposal["conversation_id"], "Approved proposal", f"Saved flow {proposal['flow']['name']}.")
    if request.run_now:
        import runner
        started_run_id = runner.start_run(flow["id"], {"_author": "assistant", "_assistant_conversation_id": proposal["conversation_id"]})
        proposal["run_id"] = started_run_id
        result.update({"run_id": started_run_id, "status": "running"})
    return result
