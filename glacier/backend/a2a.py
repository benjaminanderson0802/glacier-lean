"""Small A2A v1.0 JSON-RPC adapter for explicitly shared Glacier flows."""
import json

import runner
import store
import vault

PROTOCOL_VERSION = "1.0"


def protocol_status(status: str) -> str:
    return {"queued": "working", "running": "working", "waiting": "input-required",
            "done": "completed", "failed": "failed", "rejected": "rejected", "canceled": "canceled"}.get(status, "working")


def shared_flows() -> list[dict]:
    result = []
    for path in vault.list_notes(".json", "environments"):
        try:
            flow = json.loads(vault.read_note(path))
        except (ValueError, OSError, json.JSONDecodeError):
            continue
        if flow.get("share_a2a") is True:
            result.append(flow)
    return result


def agent_card(base_url: str) -> dict:
    skills = []
    for flow in shared_flows():
        flow_id = str(flow.get("id") or "")
        name = str(flow.get("name") or flow_id)
        description = str(flow.get("description") or f"Runs the saved {name} flow in Glacier.")
        skills.append({"id": flow_id, "name": name, "description": description,
                       "tags": ["glacier", "workflow"], "examples": [f"Run {name}"],
                       "inputModes": ["text/plain"], "outputModes": ["text/plain"]})
    return {"name": "Glacier", "description": "Glacier runs saved local workflows and returns their results.",
            "supportedInterfaces": [{"url": base_url.rstrip("/") + "/a2a", "protocolBinding": "JSONRPC",
                                      "protocolVersion": PROTOCOL_VERSION}],
            "version": "1.0.0", "capabilities": {"streaming": False, "pushNotifications": False},
            "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"], "skills": skills,
            "securitySchemes": {"engineToken": {"httpAuthSecurityScheme": {"scheme": "Bearer",
                                     "description": "Use the local Glacier install token."}}},
            "security": [{"engineToken": []}]}


def _text(message: dict) -> str:
    parts = message.get("parts") if isinstance(message, dict) else None
    if not isinstance(parts, list):
        raise ValueError("The message needs at least one text part.")
    text = "\n".join(str(p["text"]) for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str))
    if not text.strip():
        raise ValueError("The message needs some plain text.")
    return text


def _flow_for_skill(skill_id: str) -> dict | None:
    return next((f for f in shared_flows() if f.get("id") == skill_id), None)


def start_task(params: dict) -> dict:
    message = params.get("message") if isinstance(params, dict) else None
    if not isinstance(message, dict):
        raise ValueError("Include a message with a skillId and some text.")
    metadata = message.get("metadata") or {}
    skill_id = metadata.get("skillId") if isinstance(metadata, dict) else None
    if not isinstance(skill_id, str) or not skill_id:
        raise ValueError("Include the saved flow's skillId in message metadata.")
    flow = _flow_for_skill(skill_id)
    if not flow:
        raise LookupError("That shared flow is not available.")
    user_text = _text(message)
    if flow.get("goal") and not flow.get("acceptance"):
        raise ValueError("This flow has a goal but no check yet, so it cannot be started.")
    run_id = runner.start_run(skill_id, {"_author": "a2a", "_a2a_input": user_text[-8000:]})
    return task_for_run(run_id)


def _a2a_run(run_id: str) -> dict:
    """Only runs started through A2A are visible to A2A callers."""
    run = store.get_run(run_id)
    if not run or run.get("author") != "a2a":
        raise LookupError("That task could not be found.")
    return run


def task_for_run(run_id: str) -> dict:
    run = _a2a_run(run_id)
    graph = store.graph_of(run_id)
    outputs = run.get("outputs") or {}
    final_output = next((outputs[n.get("id")] for n in reversed(graph.get("nodes", []))
                         if outputs.get(n.get("id")) is not None), "")
    task = {"id": run_id, "contextId": run_id, "status": {"state": protocol_status(run["status"]),
            "timestamp": run.get("started_at") or ""}, "metadata": {"skillId": run["env_id"], "author": "a2a"}}
    if final_output is not None and final_output != "":
        task["artifacts"] = [{"artifactId": "output", "name": "Flow result", "parts": [{"text": str(final_output)}]}]
    return task


def cancel_task(run_id: str) -> dict:
    run = _a2a_run(run_id)
    if run["status"] not in ("done", "failed", "rejected", "canceled"):
        from dbos import DBOS
        try:
            DBOS.cancel_workflow(run_id)
        except Exception:
            # A just-created workflow may not yet be visible to DBOS cancellation.
            # The local run record still provides a terminal result to the caller.
            pass
        store.set_run(run_id, "canceled")
    return task_for_run(run_id)


def dispatch(request: dict) -> dict:
    req_id = request.get("id")
    if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "This request is not valid JSON-RPC."}}
    method, params = request["method"], request.get("params") or {}
    try:
        if method in ("message/send", "SendMessage"):
            result = start_task(params)
        elif method in ("tasks/get", "GetTask"):
            result = task_for_run(str(params.get("id") or ""))
        elif method in ("tasks/cancel", "CancelTask"):
            result = cancel_task(str(params.get("id") or ""))
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "This method is not supported."}}
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except LookupError as exc:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32004, "message": str(exc)}}
    except (ValueError, TypeError, AttributeError) as exc:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(exc) or "The request is missing information."}}
