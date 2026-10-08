"""Acceptance tests for owner delete actions and their audit or undo records."""
import json
import os
import subprocess
import uuid

import httpx

from conftest import raw_httpx


def _event_rows(home):
    import sqlite3
    with sqlite3.connect(os.path.join(home, "vault", ".index.sqlite")) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT data FROM events WHERE kind='delete'")]


def _audit_files(home):
    folder = os.path.join(home, "vault", "audit", "events")
    return [json.loads(open(os.path.join(folder, name), encoding="utf-8").read())
            for name in os.listdir(folder) if name.endswith(".json")] if os.path.isdir(folder) else []


def test_flow_delete_keeps_runs_and_can_be_undone(server):
    flow = {"id": "delete-flow", "name": "Delete Flow", "nodes": [{"id": "n", "type": "command", "config": {"cmd": "true"}}], "edges": []}
    server.put("/api/environments/delete-flow", flow)
    run_id = server.post("/api/environments/delete-flow/run")["run_id"]
    server.wait_run(run_id)

    deleted = httpx.delete(server.url + "/api/environments/delete-flow", timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["commit"]
    assert server.get("/api/environments") == []
    assert server.get("/api/runs", params={"env_id": "delete-flow"})[0]["run_id"] == run_id
    undone = server.post("/api/environments/delete-flow/undo-delete", {"commit": deleted.json()["commit"]})
    assert undone["restored"] is True
    assert server.get("/api/environments/delete-flow")["name"] == "Delete Flow"
    assert any(row["kind"] == "flow" and row["id"] == "delete-flow" for row in _event_rows(server.home))
    audit = next(row for row in _audit_files(server.home) if row.get("action") == "delete" and row.get("path") == "environments/delete-flow.json")
    assert audit["kind"] == "flow"
    assert subprocess.run(["git", "log", "--format=%h", "--", "audit/events"], cwd=os.path.join(server.home, "vault"), capture_output=True, text=True, check=True).stdout.split()


def test_run_delete_hides_but_keeps_run_and_is_undoable(server):
    flow = {"id": "run-delete", "name": "Run Delete", "nodes": [{"id": "n", "type": "command", "config": {"cmd": "true"}}], "edges": []}
    server.put("/api/environments/run-delete", flow)
    run_id = server.post("/api/environments/run-delete/run")["run_id"]
    server.wait_run(run_id)

    deleted = httpx.delete(server.url + f"/api/runs/{run_id}", timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert server.get("/api/runs", params={"env_id": "run-delete"}) == []
    assert server.get(f"/api/runs/{run_id}")["run_id"] == run_id
    assert server.post(f"/api/runs/{run_id}/undo-delete")["restored"] is True
    assert server.get("/api/runs", params={"env_id": "run-delete"})[0]["run_id"] == run_id
    assert any(row.get("kind") == "run" and row.get("id") == run_id for row in _event_rows(server.home))


def test_note_delete_uses_git_and_memory_undo(server):
    path = "notes/remove-me.md"
    server.put("/api/memory/note", {"path": path, "body": "# Keepable\n\nOriginal words.", "author": "owner"})
    deleted = httpx.delete(server.url + "/api/memory/note", params={"path": path}, timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["commit"]
    assert all(row["path"] != path for row in server.get("/api/memory/notes"))
    restored = server.post("/api/memory/undo-delete", {"path": path, "commit": deleted.json()["commit"]})
    assert restored["path"] == path
    assert "Original words." in server.get("/api/memory/note", params={"path": path})["body"]
    assert any(row["kind"] == "note" and row["path"] == path for row in _event_rows(server.home))


def test_note_delete_refuses_path_tricks(server):
    for path in ("../outside.md", "claims/fake-claim.md", "conversations/../outside.md"):
        response = httpx.delete(server.url + "/api/memory/note", params={"path": path}, timeout=30)
        assert response.status_code == 400, (path, response.text)


def test_every_delete_route_requires_install_token(server):
    paths = ["/api/environments/missing", "/api/runs/missing", "/api/memory/note?path=notes%2Fx.md",
             "/api/claims/2026-10-08-example-a1b2c3", f"/api/assistant/conversations/{uuid.uuid4()}",
             "/api/files?project=Inbox&name=x.txt", "/api/templates/community-x", "/api/secrets/EXAMPLE"]
    for path in paths:
        response = raw_httpx["delete"](server.url + path, timeout=30)
        assert response.status_code == 401, (path, response.status_code, response.text)


def test_claim_delete_keeps_git_history_and_can_be_undone(server):
    claim_id = server.post("/api/claims", {"kind": "bug", "summary": "Remove this claim"})["id"]
    deleted = httpx.delete(server.url + f"/api/claims/{claim_id}", timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert all(item["id"] != claim_id for item in server.get("/api/claims"))
    restored = server.post(f"/api/claims/{claim_id}/undo-delete", {"commit": deleted.json()["commit"]})
    assert restored["restored"] is True
    assert any(item["id"] == claim_id for item in server.get("/api/claims"))
    assert any(row.get("kind") == "claim" and row.get("path") == f"claims/{claim_id}.md" for row in _event_rows(server.home))


def test_conversation_delete_and_undo(server):
    conversation_id = str(uuid.uuid4())
    path = f"conversations/{conversation_id}.md"
    server.put("/api/memory/note", {"path": path,
        "body": f"# Conversation {conversation_id}\n\n## 2026-10-08T10:00:00+00:00\n\n**You:** Hello\n\n**Assistant:** Hi\n",
        "author": "owner"})
    deleted = httpx.delete(server.url + f"/api/assistant/conversations/{conversation_id}", timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert all(item["id"] != conversation_id for item in server.get("/api/assistant/conversations"))
    assert server.post(f"/api/assistant/conversations/{conversation_id}/undo-delete", {"commit": deleted.json()["commit"]})["restored"]
    assert any(row.get("kind") == "conversation" and row.get("path") == path for row in _event_rows(server.home))


def test_uploaded_file_delete_and_undo(server):
    uploaded = httpx.post(server.url + "/api/files", files={"file": ("remove.txt", b"File content", "text/plain")}, timeout=30)
    assert uploaded.status_code == 200, uploaded.text
    item = uploaded.json()
    deleted = httpx.delete(server.url + "/api/files", params={"project": item["project"], "name": item["name"]}, timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert server.get("/api/files") == []
    restored = server.post("/api/files/undo-delete", {"undo_id": deleted.json()["undo_id"]})
    assert restored["restored"] is True
    assert server.get("/api/files")[0]["name"] == "remove.txt"
    assert any(row.get("kind") == "uploaded_file" and row.get("name") == "remove.txt" for row in _event_rows(server.home))


def test_imported_template_delete_and_undo(server):
    approved = os.path.join(server.home, "templates", "approved")
    os.makedirs(approved, exist_ok=True)
    template = {"id": "community-delete-me", "name": "Imported template", "nodes": [], "edges": []}
    with open(os.path.join(approved, "proposal.json"), "w", encoding="utf-8") as stream:
        json.dump({"template": template, "author": "A contributor"}, stream)
    deleted = httpx.delete(server.url + "/api/templates/community-delete-me", timeout=30)
    assert deleted.status_code == 200, deleted.text
    assert all(item["id"] != "community-delete-me" for item in server.get("/api/templates"))
    restored = server.post("/api/templates/undo-delete", {"undo_id": deleted.json()["undo_id"]})
    assert restored["restored"] is True
    assert any(item["id"] == "community-delete-me" for item in server.get("/api/templates"))
    assert any(row.get("kind") == "imported_template" and row.get("id") == "community-delete-me" for row in _event_rows(server.home))


def test_delete_routes_refuse_path_tricks(server):
    assert httpx.delete(server.url + "/api/environments/..%2Foutside", timeout=30).status_code in (400, 404)
    assert httpx.delete(server.url + "/api/files", params={"project": "../outside", "name": "x.txt"}, timeout=30).status_code == 400
    assert httpx.delete(server.url + "/api/secrets/..%2Foutside", timeout=30).status_code in (400, 404)


def test_secret_delete_writes_name_only_audit_record(tmp_path, monkeypatch):
    import keyring
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import vault
    from routes import secrets as secrets_routes

    class MemoryKeyring(keyring.backend.KeyringBackend):
        priority = 1
        def __init__(self): self.values = {}
        def get_password(self, service, username): return self.values.get((service, username))
        def set_password(self, service, username, password): self.values[(service, username)] = password
        def delete_password(self, service, username): self.values.pop((service, username), None)

    old_vault, old_repo = vault.VAULT, vault._repo
    try:
        monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
        keyring.set_keyring(MemoryKeyring())
        vault.init(str(tmp_path / "vault"))
        app = FastAPI(); app.include_router(secrets_routes.router)
        client = TestClient(app)
        assert client.put("/api/secrets/temporary", json={"value": "secret-value"}).status_code == 200
        response = client.delete("/api/secrets/temporary")
        assert response.status_code == 200
        assert "secret-value" not in response.text
        assert any(row.get("kind") == "secret" and row.get("name") == "temporary" for row in _event_rows(str(tmp_path)))
    finally:
        vault.VAULT, vault._repo = old_vault, old_repo
