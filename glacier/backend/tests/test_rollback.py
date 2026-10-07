import json
import os
import subprocess
import sys
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
    return subprocess.check_output([sys.executable, "-c", code], env=env, text=True).strip()


def read(server, path):
    env = dict(os.environ, GLACIER_HOME=server.home)
    code = (
        "import os, vault; "
        "vault.init(os.path.join(os.environ['GLACIER_HOME'], 'vault')); "
        f"print(json.dumps(vault.read_note({path!r})))"
    )
    code = "import json; " + code
    try:
        return json.loads(subprocess.check_output([sys.executable, "-c", code], env=env, text=True, stderr=subprocess.DEVNULL))
    except subprocess.CalledProcessError:
        return None


def note_body(server, path):
    note = read(server, path)
    if note is None:
        return None
    if note.startswith("---\n"):
        _, _, remainder = note.partition("\n---\n")
        return remainder
    return note


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
    assert note_body(server, "notes/one.md") is None
    assert note_body(server, "notes/two.md") is None
    assert result["new_commit"]


def test_undo_refuses_later_owner_edit_without_changing_anything(server):
    run_id = "run-conflict-456"
    original = write(server, "notes/shared.md", "run content", f"run:{run_id}")
    owner = write(server, "notes/shared.md", "owner content", "owner")
    before = git(server.home, "rev-parse", "HEAD")

    response = httpx.post(server.url + f"/api/runs/{run_id}/undo", timeout=30)
    assert response.status_code == 409
    assert "notes/shared.md" in response.json()["detail"]
    assert note_body(server, "notes/shared.md") == "owner content"
    assert git(server.home, "rev-parse", "HEAD") == before
    assert original != owner


def test_undo_refuses_interleaved_owner_edit_and_leaves_history_unchanged(server):
    run_id = "run-interleaved-789"
    first = write(server, "notes/first.md", "run content", f"run:{run_id}")
    write(server, "notes/first.md", "owner content", "owner")
    second = write(server, "notes/second.md", "more run content", f"run:{run_id}")
    before = git(server.home, "rev-parse", "HEAD")

    response = httpx.post(server.url + f"/api/runs/{run_id}/undo", timeout=30)
    assert response.status_code == 409
    assert "notes/first.md" in response.json()["detail"]
    assert note_body(server, "notes/first.md") == "owner content"
    assert note_body(server, "notes/second.md") == "more run content"
    assert git(server.home, "rev-parse", "HEAD") == before
    assert first != second


def test_run_ids_match_exact_tag_not_prefix(server):
    write(server, "notes/longer-id.md", "belongs to longer id", "run:abc123")
    write(server, "runs/abc123.md", "runner note for longer id", "glacier-runner")
    exact = write(server, "notes/exact-id.md", "belongs to exact id", "run:abc")

    changes = server.get("/api/runs/abc/changes")
    assert [item["commit"] for item in changes] == [exact]
    assert [item["path"] for item in changes] == ["notes/exact-id.md"]

    result = server.post("/api/runs/abc/undo")
    assert result["reverted"] == [exact]
    assert note_body(server, "notes/longer-id.md") == "belongs to longer id"
    assert note_body(server, "runs/abc123.md") == "runner note for longer id"


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
