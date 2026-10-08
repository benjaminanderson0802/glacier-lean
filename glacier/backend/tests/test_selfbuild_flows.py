"""Acceptance tests for Glacier's self-build flows (PH9.1/PH9.2)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import shlex

import httpx
import pytest

import verify
from conftest import BACKEND, env

ROOT = Path(BACKEND).parents[1]
sys.path.insert(0, str(ROOT / "setup" / "selfbuild"))
import run_card as selfbuild_run_card  # noqa: E402
FEATURE = ROOT / "flows/self/feature.json"
MAINTENANCE = ROOT / "flows/self/maintenance.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_feature_and_maintenance_flows_are_valid():
    feature, maintenance = load(FEATURE), load(MAINTENANCE)
    verify.validate(feature["acceptance"])
    verify.validate(maintenance.get("acceptance"))


def test_feature_flow_has_isolated_approved_worker_and_fixed_gates():
    feature = load(FEATURE)
    codex = [n for n in feature["nodes"] if n["type"] == "codex"]
    assert codex and feature.get("isolate") is True
    assert all(n["config"].get("sandbox") == "workspace-write" for n in codex)
    approvals = {n["id"] for n in feature["nodes"] if n["type"] == "approval"}
    edges = feature["edges"]
    for worker in codex:
        assert any(e["target"] == worker["id"] and e.get("label") == "yes" and e["source"] in approvals for e in edges)
    checks = feature["acceptance"]
    commands = "\n".join(c["cmd"] for c in checks if c["kind"] == "command")
    assert "{guard}" in checks[0]["cmd"]
    assert "--baseline-root" in checks[0]["cmd"]
    assert "--repo ." in checks[0]["cmd"]
    assert all("cwd" not in check for check in checks if check["kind"] == "command")
    assert "glacier/backend && python -m pytest -q tests" in commands
    assert "pytest" in commands and "glacier/importers" in commands and "templates" in commands
    benchmark = next(c["cmd"] for c in checks if c["kind"] == "command" and "run_glacier.py" in c["cmd"])
    assert "bench/verification/run_glacier.py --results verification-results.md" in benchmark
    assert "bench/security/run_glacier.py" in commands.lower() and "security-results.md" in commands
    human = "\n".join(c.get("question", "") for c in checks if c["kind"] == "human")
    assert "Approve only if you reviewed the protected-path list above" in human
    assert "push" in feature["name"].lower() or "push" in json.dumps(feature).lower()


def test_maintenance_is_weekly_proposal_only_without_write_enabled_worker():
    flow = load(MAINTENANCE)
    raw = json.dumps(flow).lower()
    assert "health_check.py --quick" in raw
    assert "tools/scan" in raw
    assert any(n["type"] == "schedule" and n["config"].get("cron") == "0 9 * * 1" for n in flow["nodes"])
    assert all(n["config"].get("cwd") == "{repo}" for n in flow["nodes"] if n["type"] == "command")
    assert "proposal" in raw and "status_note" in raw and "results" in raw
    assert not any(n["type"] == "codex" and n.get("config", {}).get("sandbox") != "read-only"
                   for n in flow["nodes"])


def test_maintenance_acceptance_checks_the_saved_proposal_note():
    flow = load(MAINTENANCE)
    checks = flow.get("acceptance", [])
    assert len(checks) == 1
    check = checks[0]
    assert check["kind"] == "command"
    assert "GLACIER_HOME" in check["cmd"]
    assert "maintenance-" in check["cmd"] and "proposals" in check["cmd"]
    assert "Weekly maintenance proposal" in check["cmd"]
    assert "Nothing was installed or changed" in check["cmd"]


@pytest.mark.parametrize("worker_action,expected", [("delete_test", False), ("passing_change", True)])
def test_feature_run_merges_only_when_verified(server, tmp_path, worker_action, expected):
    repo = tmp_path / "toy-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    if worker_action == "delete_test":
        # A deliberately failing check proves that deleting a protected test cannot
        # turn a red baseline green: the independent guard must reject the deletion.
        baseline_text = "def test_protected_failure():\n    assert False\n"
        action = "from pathlib import Path; Path('glacier/backend/tests/test_toy.py').unlink()"
    else:
        # A separate all-green baseline lets this case exercise successful merging.
        baseline_text = "def test_ok():\n    assert True\n"
        action = "from pathlib import Path; Path('feature.txt').write_text('done\\n')"
    (repo / "test_toy.py").write_text(baseline_text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@local", "commit", "-qm", "start"], cwd=repo, check=True)
    # The running flow's isolated workspace starts from a copy of this tiny repository.
    workspace = Path(server.home) / "workspaces" / "toy"
    subprocess.run(["git", "clone", "-q", str(repo), str(workspace)], check=True)
    (workspace / "glacier/backend/tests").mkdir(parents=True)
    (workspace / "glacier/backend/tests/test_toy.py").write_bytes((repo / "test_toy.py").read_bytes())
    subprocess.run(["git", "-C", str(workspace), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(workspace), "commit", "-qm", "add protected test fixture"], check=True)
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(action)}"
    flow = env("toy", [("approve", "approval", {"prompt": "Approve starting this feature?"}),
                        ("edit", "codex", {"prompt": "Apply the requested toy change", "sandbox": "workspace-write"}),
                        ("change", "command", {"cmd": command})],
               [("approve", "edit", "yes"), ("edit", "change", "" )])
    guard = ROOT / "setup/selfbuild/protected_guard.py"
    external_guard = tmp_path / "external_guard.py"
    external_guard.write_text(guard.read_text(encoding="utf-8"), encoding="utf-8")
    # The guard's protected test paths are fixed, so stage this fixture at its protected path.
    baseline_repo = tmp_path / "baseline"; baseline_repo.mkdir()
    baseline_test = baseline_repo / "glacier/backend/tests/test_toy.py"
    baseline_test.parent.mkdir(parents=True); baseline_test.write_bytes((repo / "test_toy.py").read_bytes())
    flow.update({"goal": "Make a toy repository change", "isolate": True,
                 "acceptance": [{"kind": "command", "cmd": f"{sys.executable} {external_guard} --repo . --baseline-root {baseline_repo}"},
                                {"kind": "command", "cmd": f"{sys.executable} -m pytest -q glacier/backend/tests/test_toy.py"}]})
    server.put("/api/environments/toy", flow)
    run_id = server.post("/api/environments/toy/run")["run_id"]
    waiting = server.wait_run(run_id, ("waiting",))
    server.post(f"/api/runs/{run_id}/approve", {"node_id": "approve", "approved": True})
    run = server.wait_run(run_id)
    assert run["verified"] is expected, run.get("verification")
    assert run["workspace"]["merged"] is expected
    main_content = subprocess.check_output(["git", "-C", str(workspace), "show", "main:test_toy.py"], text=True)
    if worker_action == "passing_change":
        assert ("feature.txt" in subprocess.check_output(["git", "-C", str(workspace), "ls-tree", "-r", "--name-only", "main"], text=True)) is expected
    else:
        assert "test_protected_failure" in main_content
        branch_paths = subprocess.check_output(["git", "-C", str(workspace), "ls-tree", "-r", "--name-only", f"run/{run_id}"], text=True)
        assert "glacier/backend/tests/test_toy.py" not in branch_paths


def test_run_card_posts_card_and_prints_watch_instructions(tmp_path, capsys):
    card = tmp_path / "card.md"
    card.write_text("Build a tiny feature", encoding="utf-8")
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    seen = {}

    class API(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass
        def do_PUT(self):
            seen["flow"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"saved":true}')
        def do_POST(self):
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(b'{"run_id":"abc123"}')

    api = HTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    # A tiny source repository with a main branch, and a scratch home: the test must not depend on how the
    # outer checkout was made (CI checks out pull requests without a local main) or write into the repo.
    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    (source / "README.md").write_text("toy", encoding="utf-8")
    (source / "setup").mkdir()
    (source / "setup/requirements.txt").write_text("sample==1.0\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "start"], check=True)
    try:
        original_install = selfbuild_run_card.install_practice_requirements
        selfbuild_run_card.install_practice_requirements = lambda _repo: None
        try:
            result = selfbuild_run_card.main([str(card), "--api", f"http://127.0.0.1:{api.server_port}",
                                              "--home", str(tmp_path / "home"), "--source", str(source)])
            assert result == 0
        finally:
            selfbuild_run_card.install_practice_requirements = original_install
        output = capsys.readouterr().out
        assert "abc123" in output and "/api/runs/abc123" in output
        assert "Build a tiny feature" in seen["flow"]["nodes"][0]["config"]["cmd"]
        assert "Build a tiny feature" in seen["flow"]["nodes"][0]["config"]["cmd"]
        worker = next(node for node in seen["flow"]["nodes"] if node["type"] == "codex")
        assert "workdir" not in worker["config"]
        assert all("{repo}" not in check.get("cwd", "") for check in seen["flow"]["acceptance"])
        assert len(seen["flow"]["acceptance"]) == len(load(FEATURE)["acceptance"])
    finally:
        api.shutdown(); api.server_close()


def test_protected_guard_rejects_deleted_check(tmp_path):
    repo = tmp_path / "copy"; repo.mkdir()
    protected = repo / "glacier/backend/tests/test_guard.py"
    protected.parent.mkdir(parents=True); protected.write_text("test", encoding="utf-8")
    script = ROOT / "setup/selfbuild/protected_guard.py"
    baseline = tmp_path / "baseline"
    baseline_test = baseline / "glacier/backend/tests/test_guard.py"
    baseline_test.parent.mkdir(parents=True); baseline_test.write_text("test", encoding="utf-8")
    result = subprocess.run([sys.executable, str(script), "--repo", str(repo), "--baseline-root", str(baseline)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    protected.unlink()
    result = subprocess.run([sys.executable, str(script), "--repo", str(repo), "--baseline-root", str(baseline)], text=True, capture_output=True)
    assert result.returncode != 0 and "test_guard.py" in result.stdout


def _guard(repo, baseline):
    script = ROOT / "setup/selfbuild/protected_guard.py"
    return subprocess.run([sys.executable, str(script), "--repo", str(repo), "--baseline-root", str(baseline)],
                          text=True, capture_output=True)


def _tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_protected_guard_allows_new_tests_but_not_edits(tmp_path):
    base, repo = tmp_path / "base", tmp_path / "repo"
    _tree(base, {"glacier/backend/tests/test_a.py": "a"})
    _tree(repo, {"glacier/backend/tests/test_a.py": "a", "glacier/backend/tests/test_new.py": "new"})
    result = _guard(repo, base)
    assert result.returncode == 0, result.stdout
    assert "test_new.py" in result.stdout
    (repo / "glacier/backend/tests/test_a.py").write_text("weakened", encoding="utf-8")
    result = _guard(repo, base)
    assert result.returncode == 1 and "test_a.py" in result.stdout


def test_protected_guard_stops_for_owner_on_northstar_or_contract(tmp_path):
    base, repo = tmp_path / "base", tmp_path / "repo"
    _tree(base, {"NORTHSTAR.yaml": "v1", "glacier/contract/node_types.json": "{}"})
    _tree(repo, {"NORTHSTAR.yaml": "v1", "glacier/contract/node_types.json": "{}"})
    assert _guard(repo, base).returncode == 0
    (repo / "NORTHSTAR.yaml").write_text("v2", encoding="utf-8")
    result = _guard(repo, base)
    assert result.returncode == 2 and "needs owner approval: NORTHSTAR.yaml" in result.stdout
    (repo / "NORTHSTAR.yaml").write_text("v1", encoding="utf-8")
    _tree(repo, {"glacier/contract/extra.json": "{}"})
    assert _guard(repo, base).returncode == 2
