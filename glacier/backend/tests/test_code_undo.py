"""Undo changes merged from isolated coding runs in their flow workspace."""
import os
import subprocess

import httpx

from conftest import env


def git(workspace, *args):
    return subprocess.check_output(["git", "-C", workspace, *args], text=True).strip()


def code_flow(env_id, command):
    flow = env(env_id, [("edit", "command", {"cmd": command})], [])
    flow.update(isolate=True, goal="Update a workspace file",
                acceptance=[{"kind": "command", "cmd": "test -f answer.txt"}])
    return flow


def run_code(server, env_id, command):
    server.put(f"/api/environments/{env_id}", code_flow(env_id, command))
    run_id = server.post(f"/api/environments/{env_id}/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "done" and run["workspace"]["merged"], run
    return run_id


def test_undo_restores_isolated_run_workspace_files(server):
    env_id = "undo-code"
    workspace = os.path.join(server.home, "workspaces", env_id)
    os.makedirs(workspace)
    with open(os.path.join(workspace, "answer.txt"), "w", encoding="utf-8") as target:
        target.write("before exactly\nwith two lines\n")

    run_id = run_code(server, env_id, "printf 'after\\n' > answer.txt")
    assert open(os.path.join(workspace, "answer.txt"), encoding="utf-8").read() == "after\n"
    assert git(workspace, "log", "-1", "--format=%s").startswith(f"[run:{run_id}]")
    changes = server.get(f"/api/runs/{run_id}/changes")
    assert any(item["repo"] == "workspace" and item["path"] == "answer.txt" for item in changes)

    result = server.post(f"/api/runs/{run_id}/undo")

    assert open(os.path.join(workspace, "answer.txt"), encoding="utf-8").read() == "before exactly\nwith two lines\n"
    assert result["workspace"]["reverted"]
    assert result["workspace"]["new_commit"]
    assert "answer.txt" in result["workspace"]["changes"]


def test_undo_refuses_later_isolated_run_touching_same_file(server):
    env_id = "undo-code-conflict"
    workspace = os.path.join(server.home, "workspaces", env_id)
    os.makedirs(workspace)
    with open(os.path.join(workspace, "answer.txt"), "w", encoding="utf-8") as target:
        target.write("original\n")

    run_id = run_code(server, env_id, "printf 'first run\\n' > answer.txt")
    run_code(server, env_id, "printf 'later run\\n' > answer.txt")
    head_before = git(workspace, "rev-parse", "HEAD")

    response = httpx.post(server.url + f"/api/runs/{run_id}/undo", timeout=30)

    assert response.status_code == 409
    assert "answer.txt" in response.json()["detail"]
    assert open(os.path.join(workspace, "answer.txt"), encoding="utf-8").read() == "later run\n"
    assert git(workspace, "rev-parse", "HEAD") == head_before


def test_undo_allows_unrelated_later_isolated_run(server):
    env_id = "undo-code-unrelated"
    workspace = os.path.join(server.home, "workspaces", env_id)
    os.makedirs(workspace)
    with open(os.path.join(workspace, "answer.txt"), "w", encoding="utf-8") as target:
        target.write("original\n")

    run_id = run_code(server, env_id, "printf 'changed\\n' > answer.txt")
    run_code(server, env_id, "printf 'other\\n' > other.txt")

    result = server.post(f"/api/runs/{run_id}/undo")

    assert open(os.path.join(workspace, "answer.txt"), encoding="utf-8").read() == "original\n"
    assert open(os.path.join(workspace, "other.txt"), encoding="utf-8").read() == "other\n"
    assert result["workspace"]["reverted"]


def test_vault_only_run_undo_response_has_workspace_result(server):
    from test_rollback import write, note_body

    run_id = "undo-vault-only"
    write(server, "notes/vault-only.md", "saved note", f"run:{run_id}")

    result = server.post(f"/api/runs/{run_id}/undo")

    assert note_body(server, "notes/vault-only.md") is None
    assert result["vault"]["reverted"]
    assert result["workspace"]["reverted"] == []
