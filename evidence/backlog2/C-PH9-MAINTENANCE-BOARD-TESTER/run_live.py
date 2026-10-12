#!/usr/bin/env python3
"""Run the unchanged maintenance Environment against the disposable clone."""
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time

import httpx

evidence = Path(__file__).resolve().parent
run_root = Path((evidence / "run-root.txt").read_text().strip())
repo = run_root / "clone"
home = run_root / "home"
home.mkdir(parents=True, exist_ok=True)
py = run_root / "deps" / "py" / "bin" / "python"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
(evidence / "port.txt").write_text(f"{port}\n")
base = f"http://127.0.0.1:{port}"
env = dict(os.environ, GLACIER_HOME=str(home), GLACIER_TOKEN="ph9-maintenance-isolated-test-token",
           GLACIER_API_URL=base, PYTHONPATH=str(repo / "glacier" / "backend"))
backend_log = open(evidence / "backend.log", "w", encoding="utf-8")
server = subprocess.Popen([str(py), "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                          cwd=repo / "glacier" / "backend", env=env, stdout=backend_log,
                          stderr=subprocess.STDOUT, start_new_session=True)
result = {"port": port, "home": str(home), "clone": str(repo), "pid": server.pid}
client = httpx.Client(base_url=base, headers={"Authorization": f"Bearer {env['GLACIER_TOKEN']}"}, timeout=30)
try:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"isolated backend exited {server.returncode}")
        try:
            response = client.get("/api/environments")
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    else:
        raise RuntimeError("isolated backend did not become ready")

    flow = json.loads((repo / "flows/self/maintenance.json").read_text(encoding="utf-8"))
    for node in flow["nodes"]:
        config = node.get("config", {})
        if config.get("cwd") == "{repo}":
            config["cwd"] = str(repo)
        if config.get("cmd"):
            config["cmd"] = config["cmd"].replace("python ", shlex.quote(str(py)) + " ")
        if node.get("id") == "maintenance":
            script = repo / "setup/selfbuild/maintenance.py"
            config["cmd"] = (f"{shlex.quote(str(py))} {shlex.quote(str(script))} "
                             f"--repo {shlex.quote(str(repo))} --run {{run}}")
    for check in flow.get("acceptance", []):
        if check.get("cmd"):
            check["cmd"] = check["cmd"].replace("python ", shlex.quote(str(py)) + " ")
    response = client.put(f"/api/environments/{flow['id']}", json=flow)
    response.raise_for_status()
    started = client.post(f"/api/environments/{flow['id']}/run")
    started.raise_for_status()
    run_id = started.json()["run_id"]
    result["run_id"] = run_id
    (evidence / "run-id.txt").write_text(run_id + "\n")
    (evidence / "run-start.json").write_text(json.dumps(started.json(), indent=2) + "\n")
    deadline = time.monotonic() + 2 * 60 * 60
    while time.monotonic() < deadline:
        run = client.get(f"/api/runs/{run_id}")
        run.raise_for_status()
        payload = run.json()
        (evidence / "run-latest.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
        if payload.get("status") in {"done", "failed", "rejected", "cancelled"}:
            result["terminal_run"] = payload
            break
        time.sleep(2)
    else:
        raise TimeoutError("maintenance Environment did not reach terminal state in 2 hours")
    if payload.get("status") != "done":
        raise RuntimeError(f"maintenance Environment ended {payload.get('status')}")
    proposal_dir = home / "vault" / "proposals"
    proposals = sorted(proposal_dir.glob("maintenance-*.md")) if proposal_dir.exists() else []
    if not proposals:
        raise RuntimeError("maintenance proposal note was not saved")
    proposal = proposals[-1]
    body = proposal.read_text(encoding="utf-8")
    assert "Weekly maintenance proposal" in body
    assert "Nothing was installed or changed" in body
    assert run_id in body
    (evidence / "proposal.md").write_text(body, encoding="utf-8")
    result["proposal"] = str(proposal)
    result["proposal_acceptance"] = "passed: title, proposal-only notice, actual run ID"
    status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                            cwd=repo, capture_output=True, text=True, check=True).stdout
    (evidence / "clone-status.txt").write_text(status, encoding="utf-8")
    if status.strip():
        raise RuntimeError(f"disposable clone changed:\n{status}")
    result["clone_status"] = "clean"
finally:
    client.close()
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
    backend_log.close()
    (evidence / "live-result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
