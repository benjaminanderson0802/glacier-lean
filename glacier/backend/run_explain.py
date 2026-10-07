"""Deterministic, plain-language explanations built from a recorded run."""
import re

import secrets_store
import store


def _short_output(value: object) -> str:
    text = secrets_store.redact(str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:120].rstrip()


def _failure_advice(output: str) -> str:
    lowered = output.lower()
    if re.search(r"missing (?:secret|password)|(?:secret|password) (?:is )?missing|not set", lowered):
        return "Add the missing password in Settings > Secrets, then run again."
    if "command not found" in lowered or "is not recognized as an internal or external command" in lowered:
        return "Install the missing program, then run again."
    if "timed out" in lowered or "timeout" in lowered:
        return "The step took too long. Check its time limit or try again."
    if "check failed" in lowered or re.search(r"check .*-> no", lowered):
        return "The check did not pass. Review its result and fix the earlier step."
    if "rejected" in lowered:
        return "The request was rejected. Change the approval choice before running again."
    return "It stopped with an error. Open the step's output for details."


def explain_run(run_id: str) -> dict | None:
    run = store.get_run(run_id)
    if not run:
        return None
    graph = store.graph_of(run_id)
    import app

    labels = {item["type"]: item.get("label", item["type"]) for item in app.NODE_CATALOG}
    nodes = graph.get("nodes", [])
    steps = []
    first_failure = None
    for index, node in enumerate(nodes, 1):
        node_id = node.get("id", "")
        state = run["node_states"].get(node_id, "pending")
        label = labels.get(node.get("type"), "Step")
        output = _short_output(run["outputs"].get(node_id, ""))
        if state == "failed":
            sentence = f"Step {index} ({label}) failed: {_failure_advice(output)}"
            first_failure = first_failure or (index, label, output)
        elif state == "waiting":
            sentence = f"Step {index} ({label}) is waiting for your approval."
        elif state == "done":
            sentence = f"Step {index} ({label}) finished." + (f" {output}" if output else "")
        elif state == "skipped":
            sentence = f"Step {index} ({label}) was skipped."
        elif state == "running":
            sentence = f"Step {index} ({label}) is running."
        else:
            sentence = f"Step {index} ({label}) has not started."
        steps.append({"node_id": node_id, "label": label, "state": state, "sentence": sentence})

    checks = store.checks_of(run_id)
    acceptance = graph.get("acceptance") or []
    required = [i for i, check in enumerate(acceptance) if check.get("required", True)]
    check_results = {int(row["check"]): bool(row["passed"]) for row in checks}
    verified = None
    if run["status"] == "done" and acceptance:
        verified = all(check_results.get(i, False) for i in required)
    elif run["status"] in ("failed", "rejected"):
        verified = False

    needs_you = None
    waiting_on = run.get("waiting_on")
    if run["status"] == "waiting" and waiting_on:
        waiting_node = next((node for node in nodes if node.get("id") == waiting_on), {})
        prompt = (waiting_node.get("config") or {}).get("prompt", "").strip()
        needs_you = f"Decide whether to approve: {prompt}" if prompt else "Decide whether to approve this step."

    name = graph.get("name") or "This run"
    if run["status"] == "done":
        successful = sum(1 for step in steps if step["state"] == "done")
        summary = f"{name} finished {successful} step{'s' if successful != 1 else ''}."
        highlights = next((output for node in nodes
                           if run["node_states"].get(node.get("id")) == "done"
                           for output in [_short_output(run["outputs"].get(node.get("id"), ""))]
                           if output), "")
        if highlights:
            summary = f"{name} finished: {highlights}."
        if verified is True:
            summary += " Every check passed."
        elif verified is False:
            summary += " Some checks did not pass, so the result is not verified."
        else:
            summary += " This flow has no checks, so the result is not verified."
    elif run["status"] == "waiting":
        summary = f"{name} is waiting for your decision."
    elif run["status"] == "rejected":
        summary = f"{name} stopped because an approval was rejected."
    else:
        if first_failure:
            index, label, output = first_failure
            summary = f"Step {index} ({label}) failed. {_failure_advice(output)}"
        else:
            summary = f"{name} stopped before it finished. Open the step's output for details."

    return {"summary": summary, "steps": steps, "verified": verified, "needs_you": needs_you}
