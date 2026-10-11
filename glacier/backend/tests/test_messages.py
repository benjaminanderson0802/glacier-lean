import json
import sqlite3
import uuid

import keyring
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import secrets_store
import session_mirror
import teams
import vault
from routes import messages


class MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        del self.values[(service, username)]


@pytest.fixture
def client(tmp_path, monkeypatch, request):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    vault.init(str(tmp_path / "vault"))
    teams.init(str(tmp_path / "glacier.sqlite"))
    original_keyring = keyring.get_keyring()
    keyring.set_keyring(MemoryKeyring())
    request.addfinalizer(lambda: keyring.set_keyring(original_keyring))
    app = FastAPI()
    app.include_router(messages.router)
    return TestClient(app), tmp_path


def _team(home):
    team_id = "team-1"
    plan = {"vision": {"goal": "Build a useful tool"}, "tasks": [{"id": "task-a", "title": "Build it", "role": "builder"}]}
    state = {"status": "running", "tasks": {"task-a": {"status": "running", "output": "Started work"}},
             "progress_log": "Task task-a: running"}
    with sqlite3.connect(home / "glacier.sqlite") as db:
        db.execute("INSERT INTO glacier_teams(team_id,status,vision_path,plan,state,workspace) VALUES(?,?,?,?,?,?)",
                   (team_id, "running", "visions/one.md", json.dumps(plan), json.dumps(state), str(home)))
    return team_id


def test_threads_unify_glacier_session_and_worker_messages_and_search(client, monkeypatch):
    http, home = client
    conversation_id = str(uuid.uuid4())
    from routes import assistant_chat
    assistant_chat._append_conversation(conversation_id, "How are we doing?", "We are on track.")
    monkeypatch.setattr(session_mirror, "list_sessions", lambda: [
        {"id": "codex-1", "tool": "codex", "source": "codex", "title": "Fix a parser", "updated": "2026-10-08T10:00:00Z"},
        {"id": "claude-code:claude-1", "tool": "claude", "source": "claude", "title": "Review", "updated": "2026-10-08T09:00:00Z"},
        {"id": "opencode:open-1", "tool": "opencode", "source": "opencode", "title": "Open session", "updated": ""},
        {"id": "gemini:gemini-1", "tool": "gemini", "source": "gemini", "title": "Gemini session", "updated": ""},
    ])
    _team(home)

    rows = http.get("/api/messages/threads?q=parser").json()
    assert len(rows) == 1
    assert rows[0]["source"] == "codex"
    assert rows[0]["last_text"] == "Fix a parser"
    all_threads = http.get("/api/messages/threads").json()
    assert {row["source"] for row in all_threads} >= {"glacier", "codex", "claude", "opencode", "gemini", "worker"}
    assert all(not row["can_send"] for row in all_threads if row["source"] in {"opencode", "gemini"})

    worker = next(row for row in http.get("/api/messages/threads").json() if row["source"] == "worker")
    detail = http.get(f"/api/messages/threads/{worker['id']}").json()
    assert any(item["text"] == "Started work" for item in detail["messages"])


def test_session_detail_is_newest_first_and_secret_redacted(client, monkeypatch):
    http, _ = client
    keyring.set_keyring(keyring.get_keyring())
    keyring.get_keyring().set_password(secrets_store.SERVICE, "test-token", "shh-value")
    secrets_store._write_names(["test-token"])
    monkeypatch.setattr(session_mirror, "read_session", lambda _sid: (
        {"id": "codex-1", "source": "codex", "title": "Session", "tool": "codex"},
        [{"type": "user_message", "text": "first", "timestamp": "2026-10-08T10:00:00Z"},
         {"type": "assistant_message", "text": "shh-value", "timestamp": "2026-10-08T10:00:01Z"}], "digest"))

    response = http.get("/api/messages/threads/codex%3Acodex-1?before=2026-10-08T10:00:01Z")
    assert response.status_code == 200
    rows = response.json()["messages"]
    assert [row["text"] for row in rows] == ["first"]
    assert [row["from"] for row in rows] == ["me"]
    all_rows = http.get("/api/messages/threads/codex%3Acodex-1").json()["messages"]
    assert "shh-value" not in all_rows[0]["text"]
    assert all_rows[0]["from"] == "them"


def test_worker_send_persists_owner_instruction_and_new_glacier_chat(client, monkeypatch):
    http, home = client
    team_id = _team(home)
    thread_id = f"worker:{team_id}:task-a"
    sent = http.post(f"/api/messages/threads/{thread_id}", json={"text": "Keep the patch small."})
    assert sent.status_code == 200
    saved = teams._read(team_id)
    state = saved["state"]
    assert state["tasks"]["task-a"]["owner_notes"][0]["text"] == "Keep the patch small."
    assert "Keep the patch small." in saved["plan"]["tasks"][0]["description"]

    monkeypatch.setattr("routes.assistant_chat._ask", lambda *_: {"reply": "Ready.", "automation": False})
    monkeypatch.setattr("routes.assistant_chat.ask_route", lambda: ("codex", "test route"))
    new = http.post("/api/messages/threads", json={"source": "glacier", "text": "Hello"})
    assert new.status_code == 200
    assert new.json()["thread"]["source"] == "glacier"
    assert new.json()["message"]["text"] == "Ready."


def test_codex_and_claude_resume_use_configured_fake_commands(client, monkeypatch, tmp_path):
    http, _ = client
    codex = tmp_path / "codex-fake"
    codex.write_text("#!/bin/sh\nprintf 'Codex reply: %s\\n' \"$*\"\n")
    codex.chmod(0o755)
    claude = tmp_path / "claude-fake"
    claude.write_text("#!/bin/sh\nprintf 'Claude reply: %s\\n' \"$*\"\n")
    claude.chmod(0o755)
    monkeypatch.setenv("GLACIER_CODEX_BIN", str(codex))
    monkeypatch.setenv("GLACIER_CLAUDE_BIN", str(claude))
    monkeypatch.setattr(session_mirror, "list_sessions", lambda: [
        {"id": "codex-1", "tool": "codex", "source": "codex", "title": "Codex", "updated": ""},
        {"id": "claude-code:claude-1", "tool": "claude", "source": "claude", "title": "Claude", "updated": ""},
    ])
    monkeypatch.setattr(session_mirror, "read_session", lambda session_id: (
        {"id": session_id, "source": "claude" if session_id.startswith("claude-code:") else "codex", "tool": "codex"},
        [{"type": "user_message", "text": "Earlier request", "timestamp": "2026-10-08T10:00:00Z"}], "digest"))

    codex_response = http.post("/api/messages/threads/codex%3Acodex-1", json={"text": "Continue"})
    claude_response = http.post("/api/messages/threads/claude-code%3Aclaude-1", json={"text": "Continue"})
    assert codex_response.status_code == claude_response.status_code == 200
    assert "exec resume --all codex-1" in codex_response.json()["message"]["text"]
    assert "--resume claude-1" in claude_response.json()["message"]["text"]


def test_session_threads_explain_when_the_cli_is_missing(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(session_mirror, "list_sessions", lambda: [
        {"id": "codex-1", "source": "codex", "title": "Codex", "updated": ""},
        {"id": "claude-code:claude-1", "source": "claude", "title": "Claude", "updated": ""},
    ])
    monkeypatch.setenv("GLACIER_CODEX_BIN", "/missing/codex")
    monkeypatch.setenv("GLACIER_CLAUDE_BIN", "/missing/claude")

    rows = http.get("/api/messages/threads").json()
    assert all(row["can_send"] is False for row in rows)
    assert {row["can_send_reason"] for row in rows} == {
        "Codex CLI is not installed", "Claude CLI is not installed",
    }


def test_a_session_rejected_by_codex_becomes_read_only(client, monkeypatch, tmp_path):
    http, _ = client
    codex = tmp_path / "codex-rejecting"
    codex.write_text("#!/bin/sh\nexit 1\n")
    codex.chmod(0o755)
    monkeypatch.setenv("GLACIER_CODEX_BIN", str(codex))
    monkeypatch.setattr(session_mirror, "list_sessions", lambda: [
        {"id": "codex-rejected", "tool": "codex", "source": "codex", "title": "Old session", "updated": ""},
    ])
    monkeypatch.setattr(session_mirror, "read_session", lambda _sid: (
        {"id": "codex-rejected", "source": "codex", "tool": "codex"}, [], "digest"))

    sent = http.post("/api/messages/threads/codex%3Acodex-rejected", json={"text": "Continue"})
    assert sent.status_code == 409
    assert "cannot be continued" in sent.json()["detail"]
    thread = http.get("/api/messages/threads").json()[0]
    assert thread["can_send"] is False
    assert thread["can_send_reason"] == sent.json()["detail"]


def test_new_codex_and_claude_chats_capture_native_session_ids(client, monkeypatch, tmp_path):
    http, _ = client
    codex = tmp_path / "codex-new-fake"
    codex.write_text("#!/bin/sh\nprintf '%s\\n' '{\"type\":\"thread.started\",\"thread_id\":\"new-codex-id\"}' '{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"Codex started\"}}'\n")
    codex.chmod(0o755)
    claude = tmp_path / "claude-new-fake"
    claude.write_text("#!/bin/sh\nprintf '%s\\n' '{\"session_id\":\"new-claude-id\",\"result\":\"Claude started\"}'\n")
    claude.chmod(0o755)
    monkeypatch.setenv("GLACIER_CODEX_BIN", str(codex))
    monkeypatch.setenv("GLACIER_CLAUDE_BIN", str(claude))

    codex_response = http.post("/api/messages/threads", json={"source": "codex", "text": "Start Codex"})
    claude_response = http.post("/api/messages/threads", json={"source": "claude", "text": "Start Claude"})
    assert codex_response.status_code == claude_response.status_code == 200
    assert codex_response.json()["thread_id"] == "codex:new-codex-id"
    assert claude_response.json()["thread_id"] == "claude-code:new-claude-id"
    assert codex_response.json()["message"]["text"] == "Codex started"
    assert claude_response.json()["message"]["text"] == "Claude started"


def test_opencode_cannot_send_and_new_chat_rejects_external_sources(client):
    http, _ = client
    unavailable = http.post("/api/messages/threads/opencode%3Aopencode-1", json={"text": "No"})
    assert unavailable.status_code == 403
    invalid = http.post("/api/messages/threads", json={"source": "opencode", "text": "No"})
    assert invalid.status_code == 422
