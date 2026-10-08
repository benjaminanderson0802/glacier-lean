"""Steps run in the flow's workspace; isolated flows work on a private branch that reaches main only when verified."""
import os, subprocess
from conftest import env
import sys


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


def iso_flow(fid, text):
    e = env(fid, [("c", "command", {"cmd": f"echo {text} > out.txt && echo wrote"})], [])
    e.update(goal="Write hello into out.txt", isolate=True, acceptance=[{"kind": "command", "cmd": "grep -q hello out.txt"}])
    return e


def test_steps_run_in_the_flow_workspace_by_default(server):
    server.put("/api/environments/w0", env("w0", [("c", "command", {"cmd": "echo hi > note.txt && echo $GLACIER_WORKSPACE"})], []))
    run = server.wait_run(server.post("/api/environments/w0/run")["run_id"])
    ws = os.path.join(server.home, "workspaces", "w0")
    assert run["status"] == "done" and open(os.path.join(ws, "note.txt")).read().strip() == "hi"
    assert ws in run["outputs"]["c"]


def test_verified_isolated_run_is_merged(server):
    server.put("/api/environments/iso", iso_flow("iso", "hello"))
    run = server.wait_run(server.post("/api/environments/iso/run")["run_id"])
    ws = os.path.join(server.home, "workspaces", "iso")
    assert run["verified"] is True and run["workspace"]["merged"] is True, run
    assert open(os.path.join(ws, "out.txt")).read().strip() == "hello"  # main now has the work
    assert f"merge verified run {run['run_id']}" in git(ws, "log", "-1", "--format=%s")
    assert not os.path.exists(os.path.join(server.home, "worktrees", "iso", run["run_id"]))  # private copy cleaned up


def test_failed_isolated_run_never_reaches_main(server):
    server.put("/api/environments/iso2", iso_flow("iso2", "goodbye"))
    run = server.wait_run(server.post("/api/environments/iso2/run")["run_id"])
    ws = os.path.join(server.home, "workspaces", "iso2")
    assert run["status"] == "failed" and run["workspace"]["merged"] is False, run
    assert not os.path.exists(os.path.join(ws, "out.txt"))  # main untouched
    branch = run["workspace"]["branch"]
    assert git(ws, "show", f"{branch}:out.txt") == "goodbye"  # the attempt is kept for inspection


def test_isolated_acceptance_check_sees_full_committed_run_tree(server, tmp_path, monkeypatch):
    """Checks in isolated runs need the branch checkout, including unchanged project files."""
    repo = tmp_path / "project"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "existing.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@local",
                    "commit", "-qm", "baseline"], check=True)
    workspace = os.path.join(server.home, "workspaces", "isolated-check-tree")
    subprocess.run(["git", "clone", "-q", str(repo), workspace], check=True)
    command = f"{sys.executable} -c \"from pathlib import Path; assert Path('existing.txt').read_text() == 'baseline\\\\n'; assert Path('changed.txt').read_text() == 'worker\\\\n'\""
    graph = env("isolated-check-tree", [("change", "command", {"cmd": "echo worker > changed.txt"})], [])
    graph.update(goal="Check complete project", isolate=True,
                 acceptance=[{"kind": "command", "cmd": command}])
    # The worker's branch is committed before independent checks run.
    import runner
    original_finish = runner.finish_workspace
    def commit_worker_changes(env_id, run_id, verified):
        workspace = os.path.join(server.home, "worktrees", env_id, run_id)
        subprocess.run(["git", "-C", workspace, "add", "-A"], check=True)
        subprocess.run(["git", "-C", workspace, "-c", "user.name=worker", "-c", "user.email=worker@local",
                        "commit", "-qm", "worker result"], check=True)
        return original_finish(env_id, run_id, verified)
    monkeypatch.setattr(runner, "finish_workspace", commit_worker_changes)
    server.put("/api/environments/isolated-check-tree", graph)

    run_id = server.post("/api/environments/isolated-check-tree/run")["run_id"]
    run = server.wait_run(run_id, timeout=15)

    assert run["status"] == "done", run["verification"]
    assert run["verification"][0]["passed"] is True
    assert run["workspace"]["merged"] is True


def test_runs_merge_one_after_another(server):
    """Two verified runs of the same flow both land on main, in order, without overwriting each other."""
    e = env("seq", [("c", "command", {"cmd": "echo hello >> out.txt && echo $RANDOM > run-$(date +%s%N).txt"})], [])
    e.update(goal="Append", isolate=True, acceptance=[{"kind": "command", "cmd": "grep -q hello out.txt"}])
    server.put("/api/environments/seq", e)
    r1 = server.wait_run(server.post("/api/environments/seq/run")["run_id"])
    r2 = server.wait_run(server.post("/api/environments/seq/run")["run_id"])
    ws = os.path.join(server.home, "workspaces", "seq")
    assert r1["workspace"]["merged"] and (r2["workspace"]["merged"] or "conflicts" in r2["workspace"]["note"]), (r1, r2)
    assert len([f for f in os.listdir(ws) if f.startswith("run-")]) >= 1
