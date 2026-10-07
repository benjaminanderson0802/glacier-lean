"""Run verification benchmark cases against a locally started Glacier backend."""

from __future__ import annotations

import argparse
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
CASES = HERE / "cases"
REPO = HERE.parents[1]
PYTHON = Path("/workspaces/glacier-lean/.venv/bin/python")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(base: str, method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Glacier API {method} {path} returned {exc.code}: {detail}") from exc


def load_case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_files(root: Path, files: dict[str, str]) -> None:
    for name, contents in files.items():
        target = root.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")


def shell_quote(value: str) -> str:
    # Acceptance fixture commands are constrained by validate.py; quote workspace paths.
    import shlex
    return shlex.quote(value)


def start_backend(home: Path, port: int) -> subprocess.Popen:
    backend_dir = REPO / "glacier" / "backend"
    env = {**os.environ, "GLACIER_HOME": str(home)}
    return subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=backend_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_ready(proc: subprocess.Popen, base: str, timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Glacier backend exited during startup with status {proc.returncode}")
        try:
            request(base, "GET", "/api/node-types")
            return
        except (OSError, RuntimeError):
            time.sleep(0.25)
    raise RuntimeError("Glacier backend did not become ready within 45 seconds")


def wait_run(base: str, run_id: str, timeout: float = 180) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = request(base, "GET", f"/api/runs/{urllib.parse.quote(run_id, safe='')}")
        if result.get("status") in {"done", "failed", "rejected"}:
            return result
        time.sleep(0.25)
    raise RuntimeError(f"Run {run_id} did not finish within {timeout:g} seconds")


def run_one(base: str, home: Path, case: dict, variant: str) -> dict:
    flow_id = f"bench-{case['id']}-{variant}-{uuid.uuid4().hex[:8]}"
    solution_key = "good_solution_files" if variant == "good" else "bad_solution_files"
    workspace = home / "workspaces" / flow_id
    workspace.mkdir(parents=True, exist_ok=True)
    write_files(workspace, case["setup_files"])
    write_files(workspace, case[solution_key])
    protected = {name: content for name, content in case["setup_files"].items()
                 if name.startswith("test") or "/test" in name}
    acceptance = [{
        "kind": "command",
        "cmd": case["acceptance_check"],
        "cwd": str(workspace),
        "required": True,
        "files": protected,
    }]
    flow = {
        "id": flow_id,
        "name": f"Verification benchmark: {case['title']} ({variant})",
        "goal": case["goal"],
        "acceptance": acceptance,
        "nodes": [{"id": "write", "type": "command", "config": {
            "cmd": "true", "cwd": str(workspace)}, "position": {"x": 0, "y": 0}}],
        "edges": [],
    }
    request(base, "PUT", f"/api/environments/{urllib.parse.quote(flow_id, safe='')}", flow)
    run_id = request(base, "POST", f"/api/environments/{urllib.parse.quote(flow_id, safe='')}/run").get("run_id")
    if not run_id:
        raise RuntimeError(f"Glacier did not return a run id for {flow_id}")
    return wait_run(base, run_id)


def build_report(rows: list[dict]) -> tuple[str, float, float]:
    bad = [row for row in rows if row["variant"] == "bad"]
    good = [row for row in rows if row["variant"] == "good"]
    false_done = sum(row["verified"] is True for row in bad)
    verified_good = sum(row["verified"] is True for row in good)
    false_rate = false_done / len(bad) if bad else 0.0
    verified_rate = verified_good / len(good) if good else 0.0
    lines = ["# Glacier verification benchmark results", "",
             f"False-done rate: {false_rate:.2%} ({false_done}/{len(bad)} bad runs verified)",
             f"Verified rate: {verified_rate:.2%} ({verified_good}/{len(good)} good runs verified)", "",
             "| Case | Expected | Good verified | Bad verified |", "|---|---|---:|---:|"]
    for case_id in sorted({row["case"] for row in rows}):
        subset = [row for row in rows if row["case"] == case_id]
        expected = "trap" if any(row["variant"] == "bad" for row in subset) else "pass"
        g = next(("yes" if row["verified"] is True else "no" for row in subset if row["variant"] == "good"), "—")
        b = next(("yes" if row["verified"] is True else "no" for row in subset if row["variant"] == "bad"), "—")
        lines.append(f"| {case_id} | {expected} | {g} | {b} |")
    lines.append("")
    return "\n".join(lines), false_rate, verified_rate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Use an already-running API (useful for tests)")
    parser.add_argument("--cases", help="Comma-separated case ids; default is every case")
    parser.add_argument("--results", type=Path, default=HERE / "RESULTS.md")
    args = parser.parse_args(argv)
    paths = sorted(CASES.glob("*.yaml"))
    if args.cases:
        selected = set(args.cases.split(","))
        paths = [path for path in paths if path.stem in selected]
        missing = selected - {path.stem for path in paths}
        if missing:
            parser.error(f"unknown case ids: {', '.join(sorted(missing))}")
    cases = [load_case(path) for path in paths]
    if not cases:
        parser.error("no cases selected")
    rows = []
    temporary = tempfile.TemporaryDirectory(prefix="glacier-verification-")
    home = Path(temporary.name) / "home"
    home.mkdir()
    proc = None
    try:
        if args.base_url:
            base = args.base_url.rstrip("/")
        else:
            port = free_port()
            proc = start_backend(home, port)
            base = f"http://127.0.0.1:{port}"
            wait_ready(proc, base)
        for case in cases:
            variants = ["good"] + (["bad"] if case["trap"] != "none" else [])
            for variant in variants:
                result = run_one(base, home, case, variant)
                rows.append({"case": case["id"], "variant": variant,
                             "verified": result.get("verified"), "status": result.get("status")})
        report, false_rate, verified_rate = build_report(rows)
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(report, encoding="utf-8")
        print(report, end="")
        return 1 if false_rate >= 0.02 or verified_rate < 0.98 else 0
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        temporary.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"benchmark failed: {error}") from error
