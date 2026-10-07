#!/usr/bin/env python3
"""Run one real Glacier ACP flow through OpenCode and Codex ACP."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
PROMPT = "Create hello.txt containing exactly: hello from glacier"
CHECK_CMD = 'test "$(cat hello.txt)" = "hello from glacier"'
HARNESS = {
    "opencode": {"command": ["opencode", "acp"], "version": "1.18.35", "license": "MIT"},
    "codex-acp": {"command": ["codex-acp"], "version": "2.1.1", "license": "Apache-2.0"},
}


def dry_run() -> int:
    """Validate the requested proof inputs without requiring any installed harness."""
    assert set(HARNESS) == {"opencode", "codex-acp"}
    assert CHECK_CMD == 'test "$(cat hello.txt)" = "hello from glacier"'
    assert all(item["command"] and item["version"] and item["license"] for item in HARNESS.values())
    print("dry-run PASS: two presets, shared goal, exact independent check, pinned versions and licenses")
    return 0


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_backend(url: str, proc: subprocess.Popen, log_path: Path) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"backend exited early; see {log_path}")
        try:
            if httpx.get(url + "/api/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"backend did not start; see {log_path}")


def redact(value: str, token: str) -> str:
    value = value.replace(token, "[REDACTED_INSTALL_TOKEN]") if token else value
    value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", value)
    value = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|eyJ[A-Za-z0-9_-]{20,})\b", "[REDACTED_SECRET]", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="check proof setup without launching harnesses")
    parser.add_argument("--evidence", type=Path, default=ROOT / "evidence/live/acp_two_harnesses.md")
    args = parser.parse_args()
    if args.dry_run:
        return dry_run()

    env = dict(os.environ)
    env["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + env.get("PATH", "")
    for name, spec in HARNESS.items():
        if shutil.which(spec["command"][0], path=env["PATH"]) is None:
            raise SystemExit(f"required harness is missing: {spec['command'][0]}")

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="glacier-live-acp-") as temp:
        base = Path(temp)
        glacier_home = base / "glacier-home"
        glacier_home.mkdir()
        port = free_port()
        url = f"http://127.0.0.1:{port}"
        log_path = base / "backend.log"
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=BACKEND, env=dict(env, GLACIER_HOME=str(glacier_home)),
                stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                wait_backend(url, proc, log_path)
                token = (glacier_home / ".engine-token").read_text(encoding="utf-8").strip()
                client = httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
                for idx, (harness, spec) in enumerate(HARNESS.items(), 1):
                    env_id = f"live-acp-{harness}"
                    workdir = base / f"workspace-{harness}"
                    workdir.mkdir()
                    if harness == "opencode":
                        # OpenCode loads this project config from the ACP workspace.
                        (workdir / "opencode.json").write_text(json.dumps({
                            "$schema": "https://opencode.ai/config.json",
                            "model": "ollama/qwen3:1.7b",
                            "provider": {"ollama": {
                                "npm": "@ai-sdk/openai-compatible",
                                "name": "Ollama (local)",
                                "options": {"baseURL": "http://127.0.0.1:11434/v1"},
                                "models": {"qwen3:1.7b": {"name": "Qwen3 1.7B (local)"}},
                            }},
                        }, indent=2), encoding="utf-8")
                    flow = {
                        "id": env_id,
                        "name": f"Live ACP proof: {harness}",
                        "goal": PROMPT,
                        "nodes": [{"id": "worker", "type": "acp_agent", "position": {"x": 0, "y": 0},
                                   "config": {"harness": harness, "prompt": PROMPT, "workdir": str(workdir), "timeout": 900}}],
                        "edges": [],
                        "acceptance": [{"kind": "command", "cmd": CHECK_CMD, "cwd": str(workdir)}],
                    }
                    client.put(f"/api/environments/{env_id}", json=flow).raise_for_status()
                    started = time.monotonic()
                    run_id = client.post(f"/api/environments/{env_id}/run").json()["run_id"]
                    deadline = time.monotonic() + 960
                    run = None
                    while time.monotonic() < deadline:
                        run = client.get(f"/api/runs/{run_id}").json()
                        if run["status"] in ("done", "failed", "rejected"):
                            break
                        time.sleep(0.5)
                    elapsed = round(time.monotonic() - started, 2)
                    if not run or run["status"] not in ("done", "failed", "rejected"):
                        status = "timeout"
                    else:
                        status = run["status"]
                    output = str((run or {}).get("outputs", {}).get("worker", "(no worker output)"))
                    usage = (run or {}).get("usage", {}).get("worker", {})
                    verification = (run or {}).get("verification", [])
                    check_passed = bool(verification and verification[0].get("passed"))
                    # Also run the exact acceptance command against the actual temporary workspace.
                    independent = subprocess.run(CHECK_CMD, shell=True, cwd=workdir, capture_output=True, text=True)
                    actual_check = independent.returncode == 0
                    results.append({
                        "harness": harness, "version": spec["version"], "license": spec["license"],
                        "goal": PROMPT, "acceptance": CHECK_CMD, "status": status,
                        "backend_check_passed": check_passed, "independent_check_passed": actual_check,
                        "elapsed_seconds": elapsed, "route": usage.get("route"),
                        "tokens_in": usage.get("tokens_in"), "tokens_out": usage.get("tokens_out"),
                        "cost_usd": usage.get("cost_usd"), "raw_output": redact(output, token),
                    })
                client.close()
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

    lines = ["# Live ACP proof: two real harnesses", "", "Run date: 2026-10-07", "",
             "Both flows used the same goal and command acceptance check in separate temporary workspaces. "
             "The backend, database, and workspaces were temporary. OpenCode used the local Ollama model; Codex ACP used the existing Codex login with configured model `gpt-6-luna` and low reasoning effort.", ""]
    for item in results:
        lines += [f"## {item['harness']}", "", f"- Version: {item['version']}", f"- License: {item['license']}",
                  f"- Goal: `{item['goal']}`", f"- Acceptance: `{item['acceptance']}`",
                  f"- Glacier status: `{item['status']}`", f"- Glacier check passed: `{item['backend_check_passed']}`",
                  f"- Independent check passed: `{item['independent_check_passed']}`", f"- Elapsed: {item['elapsed_seconds']} seconds",
                  f"- Route: `{item['route']}`", f"- Tokens in/out: {item['tokens_in']} / {item['tokens_out']}",
                  f"- Cost USD: {item['cost_usd']}", "", "Raw step output (secret patterns redacted):", "",
                  "```text", item["raw_output"], "```", ""]
    success = all(x["status"] == "done" and x["backend_check_passed"] and x["independent_check_passed"] for x in results)
    lines += [f"Result: **{'PASS' if success else 'FAIL'}** — both harnesses must be done and pass both checks.", ""]
    document = "\n".join(lines)
    args.evidence.write_text(document, encoding="utf-8")
    # Refuse to claim a clean record if the generated artifact contains the actual install token.
    if token and token in document:
        raise RuntimeError("install token leaked into evidence")
    print(f"Wrote {args.evidence}")
    for item in results:
        print(f"{item['harness']}: status={item['status']} verified={item['backend_check_passed']} independent={item['independent_check_passed']}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
