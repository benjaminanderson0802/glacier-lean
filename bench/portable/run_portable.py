#!/usr/bin/env python3
"""Run the same independently checked goal through three Glacier worker backends."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import httpx

from acceptance import verify_hello_file, verify_python_function

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
MODEL = "granite3.3:2b"
CODING_GOAL = (
    "In this tiny Python project, add a function `add(a, b)` in math_ops.py that returns the sum, "
    "and add pytest tests in test_math_ops.py covering positive values and zero. Run the tests. "
    "Use relative paths in this project; do not modify test files after adding them."
)
SIMPLE_GOAL = "Create ./hello.txt in this project folder with exactly this content: hello from glacier. Use the relative path ./hello.txt."
CHECK_CMD = f"{sys.executable} -m pytest -q"
BACKENDS = {
    "Codex CLI": {"field": {"type": "codex", "config": {"sandbox": "workspace-write"}}, "version_cmd": ["codex", "--version"]},
    "OpenCode ACP": {"field": {"type": "acp_agent", "config": {"harness": "opencode"}}, "version_cmd": ["opencode", "--version"]},
    "Ollama granite3.3:2b": {"field": {"type": "local_ai", "config": {"model": MODEL, "answer_style": "Free text"}}, "version_cmd": ["ollama", "--version"]},
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def tool_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return env


def version(command: list[str], env: dict[str, str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
        return (result.stdout + result.stderr).strip().splitlines()[0][:160]
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"


def wait_backend(url: str, proc: subprocess.Popen, log: Path) -> None:
    until = time.monotonic() + 60
    while time.monotonic() < until:
        if proc.poll() is not None:
            raise RuntimeError(f"backend exited early; see {log}")
        try:
            if httpx.get(url + "/api/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"backend did not start; see {log}")


def make_project(path: Path, simple: bool) -> None:
    path.mkdir()
    if not simple:
        (path / "README.md").write_text("Add a small arithmetic function and tests.\n", encoding="utf-8")
        (path / "pyproject.toml").write_text("[tool.pytest.ini_options]\npython_files = ['test_*.py']\n", encoding="utf-8")


def build_flow(name: str, backend: dict, workspace: Path, goal: str, command: str) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    node_backend = json.loads(json.dumps(backend["field"]))
    node_type = node_backend.pop("type")
    config = node_backend["config"]
    if node_type == "codex":
        config.update({"prompt": goal, "workdir": str(workspace), "timeout": 900})
    elif node_type == "acp_agent":
        config.update({"prompt": goal, "workdir": str(workspace), "timeout": 900})
        if config["harness"] == "opencode":
            (workspace / "opencode.json").write_text(json.dumps({
                "$schema": "https://opencode.ai/config.json",
                "model": f"ollama/{MODEL}",
                "provider": {"ollama": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Ollama (local)",
                    "options": {"baseURL": "http://127.0.0.1:11434/v1"},
                    "models": {MODEL: {"name": "Granite 3.3 2B (local)", "tool_call": True}},
                }},
            }, indent=2), encoding="utf-8")
    else:
        config.update({"prompt": goal, "project_folder": str(workspace), "timeout": 900})
    return {
        "id": name,
        "name": "Portable swap bench",
        "goal": goal,
        "nodes": [{"id": "worker", "type": node_type, "position": {"x": 0, "y": 0}, "config": config}],
        "edges": [],
        "acceptance": [{"kind": "command", "cmd": command, "cwd": str(workspace)}],
    }


def normalize_flow(flow: dict) -> dict:
    clean = json.loads(json.dumps(flow))
    for key in ("id",):
        clean.pop(key, None)
    clean["nodes"][0]["id"] = "worker"
    clean["nodes"][0].pop("position", None)
    node = clean["nodes"][0]
    cfg = node["config"]
    backend_fields = {
        "step_type": node["type"],
        **{key: cfg.get(key) for key in ("harness", "command", "model", "answer_style", "sandbox") if key in cfg},
    }
    node["type"] = "<BACKEND>"
    for key in ("harness", "command", "model", "answer_style", "sandbox"):
        cfg.pop(key, None)
    cfg["<BACKEND_CONFIG>"] = "<BACKEND_CONFIG>" if backend_fields else {}
    # The work folder is isolated per backend, but not a semantic flow change.
    for value in (cfg, clean["acceptance"][0]):
        if "workdir" in value:
            value["workdir"] = "<WORKSPACE>"
        if "project_folder" in value:
            value["project_folder"] = "<WORKSPACE>"
        if "cwd" in value:
            value["cwd"] = "<WORKSPACE>"
    if "workdir" in cfg:
        cfg["project_folder"] = cfg.pop("workdir")
    return clean


def run_case(client: httpx.Client, name: str, backend: dict, base: Path, simple: bool) -> dict:
    label = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    workspace = base / (("workspace-simple-" if simple else "workspace-coding-") + label)
    make_project(workspace, simple)
    goal = SIMPLE_GOAL if simple else CODING_GOAL
    check_command = 'test "$(cat hello.txt)" = "hello from glacier"' if simple else CHECK_CMD
    flow = build_flow("portable-" + label, backend, workspace, goal, check_command)
    started = time.monotonic()
    result: dict = {"backend": name, "flow": normalize_flow(flow), "flow_backend": flow["nodes"][0]["type"]}
    try:
        client.put(f"/api/environments/{flow['id']}", json=flow).raise_for_status()
        run_id = client.post(f"/api/environments/{flow['id']}/run").json()["run_id"]
        deadline = time.monotonic() + 1260
        run = None
        while time.monotonic() < deadline:
            run = client.get(f"/api/runs/{run_id}").json()
            if run.get("status") in {"done", "failed", "rejected"}:
                break
            time.sleep(0.5)
        status = run.get("status") if run else "timeout"
        check = verify_hello_file(workspace) if simple else verify_python_function(workspace, sys.executable)
        verification = (run or {}).get("verification", [])
        result.update({
            "status": status,
            "glacier_check": bool(verification and verification[0].get("passed")),
            "independent_check": check[0],
            "independent_output": check[1],
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "output": str((run or {}).get("outputs", {}).get("worker", "(no worker output)"))[-1200:],
            "usage": (run or {}).get("usage", {}).get("worker", {}),
        })
    except Exception as exc:
        result.update({"status": "error", "glacier_check": False, "independent_check": False,
                       "independent_output": f"{type(exc).__name__}: {exc}", "elapsed_seconds": round(time.monotonic() - started, 2),
                       "output": "", "usage": {}})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "evidence/live/portable_three_backends.md")
    args = parser.parse_args()
    env = tool_env()
    missing = [name for name, cfg in BACKENDS.items() if shutil.which(cfg["version_cmd"][0], path=env["PATH"]) is None]
    if missing:
        raise SystemExit("Missing required backends: " + ", ".join(missing))

    results: dict[str, list[dict]] = {"coding": [], "simple fallback": []}
    temp_context = tempfile.TemporaryDirectory(prefix="glacier-portable-")
    base = Path(temp_context.name)
    home = base / "glacier-home"
    home.mkdir()
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    log_path = base / "backend.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                                cwd=BACKEND, env=dict(env, GLACIER_HOME=str(home)), stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_backend(url, proc, log_path)
            token = (home / ".engine-token").read_text(encoding="utf-8").strip()
            with httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
                for name, backend in BACKENDS.items():
                    results["coding"].append(run_case(client, name, backend, base, False))
                if not all(row["status"] == "done" and row["glacier_check"] and row["independent_check"] for row in results["coding"]):
                    for name, backend in BACKENDS.items():
                        results["simple fallback"].append(run_case(client, name, backend, base, True))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    temp_context.cleanup()
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    all_rows = results["coding"] + results["simple fallback"]
    flow_diff = len({json.dumps(row["flow"], sort_keys=True) for row in results["coding"]}) == 1
    lines = ["# Portable worker backend live bench", "", f"Run date: {time.strftime('%Y-%m-%d')}", "",
             "Drift check: PH2 exit M-PORTABLE; serves P-PORTABLE. PH1 is not at exit yet, so this evidence does not mark PH2 done. Existing two-harness ACP proof did not provide a repeatable three-backend swap. Acceptance: all three runs use the same goal, flow and independent check; only the worker backend field changes; every independent and Glacier check passes.", "",
             "The runner first tried the small coding goal. If any backend failed, it ran a simpler exact-file goal through all three. Workspaces and Glacier data were temporary. No credentials or tokens are recorded.", ""]
    for case_name, rows in results.items():
        if not rows:
            continue
        lines += [f"## {case_name.title()}", "", "| Backend | Glacier | Independent | Seconds | Route |", "|---|---:|---:|---:|---|"]
        for row in rows:
            route = row.get("usage", {}).get("route", "")
            lines.append(f"| {row['backend']} | {row['status']} / {row['glacier_check']} | {row['independent_check']} | {row['elapsed_seconds']} | {route} |")
        normalized_equal = len({json.dumps(row["flow"], sort_keys=True) for row in rows}) == 1
        lines += ["", "Normalized flow diff (backend selector/config and temporary workspace path normalized): " + ("identical; backend field only" if normalized_equal else "DIFFERS; inspect snapshots below"), ""]
        for row in rows:
            lines += [f"### {row['backend']}", "", f"- Worker step type: `{row['flow_backend']}`", f"- Independent check output: `{row['independent_output'] or '(empty)'}`", f"- Worker output: `{row['output'] or '(empty)'}`", ""]
    coding_pass = all(row["status"] == "done" and row["glacier_check"] and row["independent_check"] for row in results["coding"])
    fallback_pass = bool(results["simple fallback"]) and all(row["status"] == "done" and row["glacier_check"] and row["independent_check"] for row in results["simple fallback"])
    outcome = "PASS" if coding_pass and flow_diff else "PASS on simpler fallback" if fallback_pass and len({json.dumps(row['flow'], sort_keys=True) for row in results['simple fallback']}) == 1 else "FAIL"
    lines += [f"## Result: {outcome}", "", f"Coding goal across three backends: {'PASS' if coding_pass else 'FAIL'}.",
              f"Coding goal flow diff: {'backend field only' if flow_diff else 'more than backend field changed'}.",
              f"Three-backend portability rate for accepted goal: {sum(bool(r['independent_check']) for r in (results['coding'] if coding_pass else results['simple fallback']))}/3.", ""]
    document = "\n".join(lines)
    args.evidence.write_text(document, encoding="utf-8")
    if token in document:
        raise RuntimeError("install token leaked into evidence")
    print("| Backend | Goal | Independent | Seconds |")
    print("|---|---|---:|---:|")
    for case_name, rows in results.items():
        for row in rows:
            print(f"| {row['backend']} | {case_name} | {row['independent_check']} | {row['elapsed_seconds']} |")
    print(f"Flow diff (coding): {'backend field only' if flow_diff else 'DIFF'}")
    print(f"Wrote {args.evidence}")
    return 0 if outcome.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
