import json
import os
import subprocess
import time

import httpx

def git(home, *args):
    return subprocess.check_output(["git", "-C", os.path.join(home, "vault"), *args], text=True).strip()


def write(server, path, body, author):
    env = dict(os.environ, GLACIER_HOME=server.home)
    code = (
        "import os, vault; "
        "vault.init(os.path.join(os.environ['GLACIER_HOME'], 'vault')); "
        f"print(vault.write_note({path!r}, {body!r}, {author!r}))"
    )
    return subprocess.check_output(["/workspaces/glacier-lean/.venv/bin/python", "-c", code], env=env, text=True).strip()


def test_run_changes_are_listed_and_undone_together(server):
    run_id = "run-notes-123"
    first = write(server, "notes/one.md", "one", f"run:{run_id}")
    second = write(server, "notes/two.md", "two", f"run:{run_id}")

    changes = server.get(f"/api/runs/{run_id}/changes")
    assert {c["commit"] for c in changes} == {first, second}
    assert {c["path"] for c in changes} == {"notes/one.md", "notes/two.md"}

    started = time.monotonic()
    result = server.post(f"/api/runs/{run_id}/undo")
    assert time.monotonic() - started < 120
    assert set(result["reverted"]) == {first, second}
    assert not os.path.exists(os.path.join(server.home, "vault", "notes/one.md"))
    assert not os.path.exists(os.path.join(server.home, "vault", "notes/two.md"))
    assert result["new_commit"]


def test_undo_refuses_later_owner_edit_without_changing_anything(server):
    run_id = "run-conflict-456"
    original = write(server, "notes/shared.md", "run content", f"run:{run_id}")
    owner = write(server, "notes/shared.md", "owner content", "owner")
    before = git(server.home, "rev-parse", "HEAD")

    response = httpx.post(server.url + f"/api/runs/{run_id}/undo", timeout=30)
    assert response.status_code == 409
    assert "notes/shared.md" in response.json()["detail"]
    assert open(os.path.join(server.home, "vault", "notes/shared.md")).read() == "owner content"
    assert git(server.home, "rev-parse", "HEAD") == before
    assert original != owner


def test_restore_flow_to_an_earlier_saved_version(server):
    flow = {"id": "restore-me", "name": "Before", "nodes": [], "edges": []}
    first = server.put("/api/environments/restore-me", flow)
    flow["name"] = "After"
    server.put("/api/environments/restore-me", flow)

    result = server.post("/api/environments/restore-me/restore", {"commit": first["commit"]})
    assert result["new_commit"]
    assert result["new_commit"] != first["commit"]
    assert server.get("/api/environments/restore-me")["name"] == "Before"
    assert json.loads(git(server.home, "show", f"{result['new_commit']}:environments/restore-me.json"))["name"] == "Before"
