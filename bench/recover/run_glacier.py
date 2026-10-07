"""Measure local API recovery latency and audit coverage for Glacier."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PYTHON = Path(os.environ.get("GLACIER_PYTHON") or sys.executable)
LIMIT_SECONDS = 120
CASES = [
    {"id": "run_notes", "title": "run writes 50 notes", "recovery_path": "/api/runs/{run_id}/undo"},
    {"id": "flow_restore", "title": "restore an earlier flow version", "recovery_path": "/api/environments/{env_id}/restore"},
    {"id": "memory_undo", "title": "undo an overwritten memory note", "recovery_path": "/api/memory/undo"},
    {"id": "isolated_code_undo", "title": "undo an isolated coding run merged into workspace", "recovery_path": "/api/runs/{run_id}/undo"},
]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(base: str, method: str, path: str, body: dict | None = None, timeout: float = 10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Glacier API {method} {path} returned {exc.code}: {detail}") from exc


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_snapshot(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    excluded = {"index.sqlite", "memory-index.sqlite", "memory_index.sqlite", "index.db", "memory.db"}
    return {p.relative_to(root).as_posix(): file_hash(p) for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts and p.name.casefold() not in excluded}


def load_runner() -> object:
    """Load the verification runner by file path, under a unique module name."""
    path = REPO / "bench" / "verification" / "run_glacier.py"
    name = f"verification_runner_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_backend(home: Path, port: int) -> subprocess.Popen:
    backend_dir = REPO / "glacier" / "backend"
    env = {k: v for k, v in os.environ.items() if k not in {"CODEX_HOME", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}}
    env.update({"GLACIER_HOME": str(home), "GLACIER_CODEX_BIN": str(HERE / "fake_codex.py"),
                "GLACIER_SANDBOX": "off", "CODEX_BIN": str(HERE / "fake_codex.py"),
                "PYTHONUNBUFFERED": "1"})
    return subprocess.Popen([str(PYTHON), "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=backend_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                            start_new_session=True)


def wait_ready(proc: subprocess.Popen, base: str) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Backend exited during startup ({proc.returncode})")
        try:
            request(base, "GET", "/api/node-types", timeout=2)
            return
        except (OSError, RuntimeError):
            time.sleep(.25)
    raise RuntimeError("Backend did not become ready within 45 seconds")


def wait_run(base: str, run_id: str, timeout: float = 60) -> dict:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        run = request(base, "GET", f"/api/runs/{urllib.parse.quote(run_id, safe='')}")
        if run.get("status") in {"done", "failed", "rejected"}:
            return run
        time.sleep(.2)
    raise RuntimeError(f"Run {run_id} did not finish")


def flow(env_id: str, cmd: str, isolate: bool = False) -> dict:
    return {"id": env_id, "name": env_id, "nodes": [{"id": "write", "type": "command",
            "config": {"cmd": cmd, "cwd": str(Path(os.environ["GLACIER_HOME"]) / "workspaces" / env_id)},
            "position": {"x": 0, "y": 0}}], "edges": [], "isolate": isolate}


def save_flow(base: str, env_id: str, value: dict) -> str:
    result = request(base, "PUT", f"/api/environments/{urllib.parse.quote(env_id, safe='')}", value)
    return result["commit"]


def git_audit(root: Path, run_id: str) -> tuple[int, set[str]]:
    result = subprocess.run(["git", "-C", str(root), "log", "--format=%H%x09%s", "--name-only"],
                            capture_output=True, text=True, check=True)
    commits = 0
    paths: set[str] = set()
    matching = False
    for line in result.stdout.splitlines():
        if "\t" in line:
            matching = f"[run:{run_id}]" in line or f"run {run_id}" in line.casefold()
            if matching:
                commits += 1
        elif matching and line.strip():
            paths.add(line.strip())
    return commits, paths


def timed_recovery(action, verify):
    started = time.monotonic()
    error = ""
    try:
        action()
    except (RuntimeError, OSError) as exc:
        error = str(exc)
    deadline = started + LIMIT_SECONDS
    while True:
        try:
            restored = bool(verify())
        except (OSError, ValueError, KeyError):
            restored = False
        if restored:
            return time.monotonic() - started, True, error
        now = time.monotonic()
        if now >= deadline:
            return now - started, False, error
        time.sleep(min(0.1, deadline - now))


def expected_audit_count(changed_files: int) -> int:
    """Count run side effects only; the later undo request is not a run effect."""
    return changed_files


def audit_paths_for_run(repo_root: Path, run_id: str) -> set[str]:
    """Return paths in commits explicitly associated with this run."""
    result = subprocess.run(["git", "-C", str(repo_root), "log", "--all", "--format=%H%x09%s", "--name-only"],
                            capture_output=True, text=True, check=True)
    paths: set[str] = set()
    matching = False
    for line in result.stdout.splitlines():
        if "\t" in line:
            message = line.split("\t", 1)[1].casefold()
            matching = f"[run:{run_id}]" in message or f"run {run_id}" in message
        elif matching and line.strip():
            paths.add(line.strip())
    return paths


def exercise(base: str, home: Path) -> list[dict]:
    rows = []
    # Case 1: one real run with fifty note nodes, each producing a run-tagged file.
    env_id = "recover-notes-" + uuid.uuid4().hex[:8]
    nodes = [{"id": f"note-{i:02d}", "type": "note",
              "config": {"path": f"runs/{env_id}-{i:02d}-{{run}}.md", "template": f"benchmark note {i} for {{run}}"},
              "position": {"x": 0, "y": 0}} for i in range(50)]
    runflow = {"id": env_id, "name": env_id, "nodes": nodes, "edges": []}
    save_flow(base, env_id, runflow)
    run_id = request(base, "POST", f"/api/environments/{env_id}/run")["run_id"]
    run = wait_run(base, run_id)
    if run.get("status") != "done":
        raise RuntimeError(f"50-note run ended with status {run.get('status')}")
    vault_root = home / "vault"
    paths = sorted(p for p in (vault_root / "runs").glob(f"{env_id}-*-{run_id}.md"))
    before = {p: file_hash(p) for p in paths}
    if len(before) != 50:
        raise RuntimeError(f"50-note run created {len(before)} notes instead of 50")
    audit_paths = audit_paths_for_run(vault_root, run_id)
    elapsed, recovered, recovery_error = timed_recovery(lambda: request(base, "POST", f"/api/runs/{run_id}/undo"),
                                        lambda: all(not p.exists() for p in paths))
    rows.append({"id": "run_notes", "seconds": elapsed, "recovered": recovered,
                 "audit_expected": expected_audit_count(len(before)), "audit_found": len(audit_paths),
                 "detail": f"one run; {len(before)} note files hashed and removed; audit paths={len(audit_paths)}" + (f"; recovery error: {recovery_error}" if recovery_error else "")})

    # Case 2: version a flow through ten edits and restore its first version.
    env_id = "recover-flow-" + uuid.uuid4().hex[:8]
    original = {"id": env_id, "name": "original", "nodes": [], "edges": []}
    old_commit = save_flow(base, env_id, original)
    flow_path = home / "vault" / "environments" / f"{env_id}.json"
    original_bytes = flow_path.read_bytes()
    versions = []
    for i in range(10):
        updated = {**original, "name": f"edit-{i + 1}"}
        versions.append(save_flow(base, env_id, updated))
    start_hash = file_hash(flow_path)
    env_rel = f"environments/{env_id}.json"
    flow_history_before = subprocess.run(["git", "-C", str(home / "vault"), "log", "--format=%H",
                                          "--", f"environments/{env_id}.json"],
                                         capture_output=True, text=True, check=True).stdout.splitlines()
    elapsed, recovered, recovery_error = timed_recovery(
        lambda: request(base, "POST", f"/api/environments/{env_id}/restore", {"commit": old_commit}),
        lambda: flow_path.read_bytes() == original_bytes)
    rows.append({"id": "flow_restore", "seconds": elapsed, "recovered": recovered,
                 "audit_expected": expected_audit_count(len(versions)),
                 "audit_found": max(0, len(flow_history_before) - 1), "detail": f"restored exact original bytes; edited hash {start_hash[:12]} -> {file_hash(flow_path)[:12]}" + (f"; recovery error: {recovery_error}" if recovery_error else "")})

    # Case 3: overwrite then undo a memory note to its exact prior bytes.
    note_path = "bench/recovery-note.md"
    request(base, "PUT", "/api/memory/note", {"path": note_path, "body": "# Original\n\nfirst body", "author": "owner"})
    prior_hash = file_hash(home / "vault" / note_path)
    overwrite = request(base, "PUT", "/api/memory/note", {"path": note_path, "body": "# Changed\n\nsecond body", "author": "owner"})
    note_file = home / "vault" / note_path
    expected = 1
    history_before = subprocess.run(["git", "-C", str(home / "vault"), "log", "--format=%H",
                                     "--", note_path], capture_output=True, text=True, check=True).stdout.splitlines()
    elapsed, recovered, recovery_error = timed_recovery(lambda: request(base, "POST", "/api/memory/undo", {"path": note_path, "commit": overwrite["commit"]}),
                                        lambda: file_hash(note_file) == prior_hash)
    rows.append({"id": "memory_undo", "seconds": elapsed, "recovered": recovered,
                 "audit_expected": expected_audit_count(expected),
                 "audit_found": max(0, len(history_before) - 1), "detail": f"restored exact prior hash {prior_hash[:12]}" + (f"; recovery error: {recovery_error}" if recovery_error else "")})

    # Case 4: isolated command run creates a file, merges it, then run undo restores workspace.
    env_id = "recover-code-" + uuid.uuid4().hex[:8]
    workspace = home / "workspaces" / env_id
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "answer.txt"
    target.write_text("before\n", encoding="utf-8")
    before_hash = file_hash(target)
    cmd = "python -c \"from pathlib import Path; Path('answer.txt').write_text('after\\\\n')\""
    codeflow = {"id": env_id, "name": env_id, "isolate": True, "nodes": [{"id": "write", "type": "command",
        "config": {"cmd": cmd}, "position": {"x": 0, "y": 0}}], "edges": []}
    save_flow(base, env_id, codeflow)
    run_id = request(base, "POST", f"/api/environments/{env_id}/run")["run_id"]
    result = wait_run(base, run_id)
    if not result.get("workspace", {}).get("merged"):
        raise RuntimeError(f"Isolated run did not merge: {result.get('workspace')}")
    after_hash = file_hash(target)
    audit_paths = audit_paths_for_run(workspace, run_id)
    workspace_head = subprocess.run(["git", "-C", str(workspace), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    workspace_paths = subprocess.run(["git", "-C", str(workspace), "diff", "--name-only", f"{workspace_head}^1", workspace_head], capture_output=True, text=True, check=True).stdout.splitlines()
    elapsed, recovered, recovery_error = timed_recovery(lambda: request(base, "POST", f"/api/runs/{run_id}/undo"),
                                        lambda: file_hash(target) == before_hash)
    rows.append({"id": "isolated_code_undo", "seconds": elapsed, "recovered": recovered,
                 "audit_expected": expected_audit_count(len(workspace_paths)), "audit_found": len(audit_paths),
                 "detail": f"workspace changed files={len(workspace_paths)}; git audit paths={len(audit_paths)}; workspace hash {before_hash[:12]} -> {after_hash[:12]} -> {file_hash(target)[:12]}" + (f"; recovery error: {recovery_error}" if recovery_error else "")})
    return rows


def build_report(rows: list[dict]) -> tuple[str, bool]:
    expected = sum(row["audit_expected"] for row in rows)
    found = sum(min(row["audit_expected"], row["audit_found"]) for row in rows)
    coverage = 100.0 if expected == 0 else 100 * found / expected
    passed = all(row["recovered"] and row["seconds"] <= LIMIT_SECONDS for row in rows) and coverage >= 100
    lines = ["# Recovery benchmark results", "", "Local backend, fake Codex executable, HTTP API requests. Recovery latency starts immediately before the undo/restore request and ends after independent file-state verification.", "",
             f"Audit coverage: {coverage:.2f}% ({found}/{expected} expected side effects found)", "", "| Scenario | Recovery time | Restored state | Audit entries expected/found | Result |", "|---|---:|---|---:|---|"]
    for row in rows:
        ok = row["recovered"] and row["seconds"] <= LIMIT_SECONDS and row["audit_found"] >= row["audit_expected"]
        lines.append(f"| {row['id']} | {row['seconds']:.3f} s | {'PASS' if row['recovered'] else 'FAIL'} | {row['audit_expected']}/{row['audit_found']} | {'PASS' if ok else 'FAIL'} |")
        lines.append(f"\n{row['id']} detail: {row['detail']}")
    lines.extend(["", f"Threshold: each recovery <= {LIMIT_SECONDS} s; total audit coverage 100%.", f"Overall: {'PASS' if passed else 'FAIL'}", ""])
    return "\n".join(lines), passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "RESULTS.md")
    args = parser.parse_args(argv)
    temp = tempfile.TemporaryDirectory(prefix="glacier-recover-")
    home = Path(temp.name) / "home"
    home.mkdir()
    port = free_port()
    proc = start_backend(home, port)
    base = f"http://127.0.0.1:{port}"
    try:
        wait_ready(proc, base)
        rows = exercise(base, home)
        report, passed = build_report(rows)
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(report, encoding="utf-8")
        print(report, end="")
        return 0 if passed else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
        temp.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError, KeyError) as error:
        raise SystemExit(f"benchmark failed: {error}") from error
