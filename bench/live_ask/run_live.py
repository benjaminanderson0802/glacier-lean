#!/usr/bin/env python3
"""Exercise the Ask screen's HTTP contract against a local Glacier backend."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

import requests

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
QUESTION = "What can you do for me?"
BACKUP = "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed"


def requests_session():
    return requests.Session()


def _events(response):
    collected, first_text, proposal, error, finished = [], None, None, None, False
    start = time.perf_counter()
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        event = json.loads(line[6:])
        collected.append(event)
        if event.get("type") == "TEXT_MESSAGE_CONTENT":
            if first_text is None:
                first_text = time.perf_counter() - start
        elif event.get("type") == "TOOL_CALL_ARGS":
            try:
                proposal = json.loads(event.get("delta", ""))
            except json.JSONDecodeError:
                pass
        elif event.get("type") == "RUN_ERROR":
            error = event.get("message", "The assistant could not answer. Please try again.")
        elif event.get("type") == "RUN_FINISHED":
            finished = True
    return {"events": collected, "proposal": proposal, "error": error, "finished": finished,
            "first_text_seconds": first_text, "total_seconds": time.perf_counter() - start}


class Client:
    def __init__(self, base, token, session=None):
        self.base, self.session = base.rstrip("/"), session or requests_session()
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def chat(self, message, conversation_id=None):
        payload = {"message": message, "conversation_id": conversation_id or str(uuid.uuid4())}
        with self.session.post(self.base + "/api/assistant/chat", json=payload,
                                headers=self.headers, stream=True, timeout=900) as response:
            response.raise_for_status()
            return _events(response)

    def apply(self, proposal_id, approve):
        response = self.session.post(self.base + f"/api/assistant/proposals/{proposal_id}/apply",
                                     json={"approve": approve}, headers=self.headers, timeout=60)
        response.raise_for_status()
        return response.json()

    def environments(self):
        response = self.session.get(self.base + "/api/environments", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()


def _run_sequence(client, validate_only=False):
    result = {"question": {}, "proposal": {}, "approve": {}, "reject": {}, "bad_proposal": {}}
    q = client.chat(QUESTION)
    text = "".join(e.get("delta", "") for e in q["events"] if e.get("type") == "TEXT_MESSAGE_CONTENT")
    result["question"] = {"passed": bool(text) and q["finished"] and not q["error"], "text": text,
                          "error": q["error"], "first_text_seconds": q["first_text_seconds"], "total_seconds": q["total_seconds"]}

    p = client.chat(BACKUP)
    proposal = p["proposal"]
    valid = bool(proposal and proposal.get("flow", {}).get("acceptance"))
    result["proposal"] = {"passed": valid and p["finished"] and not p["error"], "raw": proposal,
                          "error": p["error"], "first_text_seconds": p["first_text_seconds"], "total_seconds": p["total_seconds"]}
    if not proposal:
        result["approve"] = {"passed": False, "error": "No proposal to approve"}
        result["reject"] = {"passed": False, "error": "No proposal to reject"}
        return result
    flow = proposal["flow"]
    if validate_only:
        import app
        try:
            app.validate_environment(flow.get("id") or "live-ask-validation", flow)
            result["proposal"]["backend_validation"] = "passed"
        except Exception as exc:
            result["proposal"]["backend_validation"] = f"failed: {exc}"
            result["proposal"]["passed"] = False
        return result

    apply = client.apply(proposal["id"], True)
    exists = any(env["id"] == flow["id"] for env in client.environments())
    result["approve"] = {"passed": apply.get("saved") is True and exists, "response": apply, "flow_exists": exists}
    second = client.chat(BACKUP)
    second_proposal = second["proposal"]
    result["bad_proposal"] = {"passed": bool(second["error"] and isinstance(second["error"], str)) or
                               (second["finished"] and bool(second_proposal)), "raw": second_proposal,
                               "error": second["error"],
                               "user_message": second["error"] or ("Proposal shown for review" if second_proposal else "No plain-language reply")}
    if second_proposal:
        before = client.environments()
        rejected = client.apply(second_proposal["id"], False)
        after = client.environments()
        result["reject"] = {"passed": rejected.get("discarded") is True and before == after,
                             "response": rejected, "no_flow_created": before == after}
    else:
        result["reject"] = {"passed": False, "error": second["error"] or "No second proposal"}
    return result


def run_dry(session=None):
    if session is None:
        from unittest.mock import patch
        from test_run_live import FakeSession
        session = FakeSession()
    client = Client("http://fake.invalid", "dry-token", session=session)
    result = _run_sequence(client)
    result["dry_run"] = True
    return result


def _port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_backend(home, model):
    port = _port()
    env = dict(os.environ, GLACIER_HOME=str(home), GLACIER_LOCAL_MODEL=model)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Backend exited during startup: " + (proc.stdout.read() if proc.stdout else ""))
        try:
            if requests.get(base + "/api/health", timeout=1).ok:
                token = (home / ".engine-token").read_text().strip()
                return proc, Client(base, token)
        except (requests.RequestException, FileNotFoundError):
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("Backend did not become ready in 90 seconds")


def _one_live(model):
    home = Path(tempfile.mkdtemp(prefix="glacier-live-ask-"))
    proc = None
    try:
        proc, client = _start_backend(home, model)
        return _run_sequence(client)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        shutil.rmtree(home, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="run the no-network contract check")
    parser.add_argument("--model", default="granite3.3:2b")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps(run_dry(), indent=2, ensure_ascii=False)); return
    reports = []
    for index in range(args.runs):
        try: reports.append({"run": index + 1, "result": _one_live(args.model)})
        except Exception as exc: reports.append({"run": index + 1, "startup_error": str(exc)})
    output = {"model": args.model, "runs": reports}
    rendered = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output: args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__": main()
