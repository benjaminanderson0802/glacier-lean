import json
import logging
import sqlite3
from datetime import datetime, timezone

import keyring
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import secrets_store
import vault
from routes import sessions


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
def session_client(tmp_path, monkeypatch, request):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    data = tmp_path / "opencode-data"
    data.mkdir()
    monkeypatch.setenv("GLACIER_CODEX_SESSIONS", str(tmp_path / "no-codex-sessions"))
    monkeypatch.setenv("GLACIER_OPENCODE_DATA", str(data))
    original = keyring.get_keyring()
    keyring.set_keyring(MemoryKeyring())
    request.addfinalizer(lambda: keyring.set_keyring(original))
    vault.init(str(tmp_path / "vault"))
    app = FastAPI()
    app.include_router(sessions.router)
    return TestClient(app), data, tmp_path


def make_database(data, *, malformed=False):
    path = data / "opencode.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE project (
            id text PRIMARY KEY, worktree text NOT NULL, vcs text, name text,
            icon_url text, icon_url_override text, icon_color text,
            time_created integer NOT NULL, time_updated integer NOT NULL,
            time_initialized integer, sandboxes text NOT NULL, commands text
        );
        CREATE TABLE session (
            id text PRIMARY KEY, project_id text NOT NULL, workspace_id text, parent_id text,
            slug text NOT NULL, directory text NOT NULL, path text, title text NOT NULL,
            version text NOT NULL, share_url text, summary_additions integer,
            summary_deletions integer, summary_files integer, summary_diffs text, metadata text,
            cost real DEFAULT 0 NOT NULL, tokens_input integer DEFAULT 0 NOT NULL,
            tokens_output integer DEFAULT 0 NOT NULL, tokens_reasoning integer DEFAULT 0 NOT NULL,
            tokens_cache_read integer DEFAULT 0 NOT NULL, tokens_cache_write integer DEFAULT 0 NOT NULL,
            revert text, permission text, agent text, model text,
            time_created integer NOT NULL, time_updated integer NOT NULL,
            time_compacting integer, time_archived integer
        );
        CREATE TABLE message (
            id text PRIMARY KEY, session_id text NOT NULL, time_created integer NOT NULL,
            time_updated integer NOT NULL, data text NOT NULL
        );
        CREATE TABLE part (
            id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
            time_created integer NOT NULL, time_updated integer NOT NULL, data text NOT NULL
        );
    """)
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    connection.execute("INSERT INTO project VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("prj", "/work/project", "git", "project", None, None, None, now, now, now, "[]", None))
    connection.execute("""INSERT INTO session
        (id, project_id, slug, directory, title, version, time_created, time_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("session-one", "prj", "sample", "/work/project", "OpenCode work", "1.18.34", now - 3000, now))
    if malformed:
        connection.execute("INSERT INTO message VALUES (?, ?, ?, ?, ?)", ("bad", "session-one", now, now, "not-json"))
    else:
        user = {"id": "msg_user", "sessionID": "session-one", "role": "user", "time": {"created": now - 2000}}
        assistant = {"id": "msg_assistant", "sessionID": "session-one", "role": "assistant", "time": {"created": now - 1000, "completed": now - 500}, "parentID": "msg_user", "modelID": "model", "providerID": "test", "mode": "build", "agent": "build", "path": {"cwd": "/work/project", "root": "/work/project"}, "cost": 0, "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}}}
        connection.execute("INSERT INTO message VALUES (?, ?, ?, ?, ?)", ("msg_user", "session-one", now - 2000, now - 2000, json.dumps(user)))
        connection.execute("INSERT INTO message VALUES (?, ?, ?, ?, ?)", ("msg_assistant", "session-one", now - 1000, now - 1000, json.dumps(assistant)))
        records = [
            ("prt_user", "msg_user", {"id": "prt_user", "sessionID": "session-one", "messageID": "msg_user", "type": "text", "text": "Please inspect opencode-secret"}, now - 2000),
            ("prt_tool", "msg_assistant", {"id": "prt_tool", "sessionID": "session-one", "messageID": "msg_assistant", "type": "tool", "callID": "call-1", "tool": "bash", "state": {"status": "completed", "input": {"command": "pytest -q"}, "output": "2 passed", "title": "Run tests", "metadata": {}, "time": {"start": now - 900, "end": now - 800}}}, now - 900),
            ("prt_assistant", "msg_assistant", {"id": "prt_assistant", "sessionID": "session-one", "messageID": "msg_assistant", "type": "text", "text": "Found opencode-secret"}, now - 700),
        ]
        for part_id, message_id, value, stamp in records:
            connection.execute("INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
                               (part_id, message_id, "session-one", stamp, stamp, json.dumps(value)))
    connection.commit()
    connection.close()
    return path


def test_combines_codex_and_opencode_without_id_collisions(session_client, tmp_path):
    client, data, _ = session_client
    make_database(data)
    from session_readers import opencode
    codex = tmp_path / "no-codex-sessions"
    codex.mkdir()
    (codex / "session-one.jsonl").write_text(json.dumps({"type": "session_meta", "payload": {"id": "session-one", "cwd": "/codex"}}) + "\n")

    rows = client.get("/api/sessions").json()
    assert {row["id"] for row in rows} == {"session-one", "opencode:session-one"}
    codex_row = next(row for row in rows if row["id"] == "session-one")
    assert "source" not in codex_row
    opencode_row = next(row for row in rows if row["id"] == "opencode:session-one")
    assert opencode_row["id"] == "opencode:session-one"
    assert opencode_row["tool"] == opencode_row["source"] == "opencode"
    assert opencode_row["title"] == "Please inspect opencode-secret"
    assert opencode_row["cwd"] == "/work/project"
    assert opencode_row["active"] is True
    assert opencode_row["started"] < opencode_row["updated"]


def test_detail_orders_messages_and_tool_calls_and_redacts_saved_note(session_client):
    client, data, home = session_client
    make_database(data)
    keyring.set_keyring(MemoryKeyring())
    keyring.set_password(secrets_store.SERVICE, "session-token", "opencode-secret")
    secrets_store._write_names(["session-token"])

    response = client.get("/api/sessions/opencode:session-one")
    assert response.status_code == 200
    detail = response.json()
    assert [event["type"] for event in detail["events"]] == ["user_message", "command", "command_output", "assistant_message"]
    assert detail["events"][0]["text"] == "Please inspect [secret session-token]"
    assert detail["events"][1]["text"] == "Ran command: Run tests"
    assert detail["events"][2]["text"] == "2 passed"
    assert detail["events"][3]["text"] == "Found [secret session-token]"

    saved = client.post("/api/sessions/opencode:session-one/save-to-memory")
    assert saved.status_code == 200 and saved.json()["saved"] is True
    note = (home / "vault" / saved.json()["path"]).read_text()
    assert "**User:** Please inspect [secret session-token]" in note
    assert "**Command:** Ran command: Run tests" in note
    assert "**Command output:** 2 passed" in note
    assert "**OpenCode:** Found [secret session-token]" in note
    assert "opencode-secret" not in note


def test_missing_database_and_directory_return_no_opencode_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_OPENCODE_DATA", str(tmp_path / "missing"))
    from session_readers import opencode
    assert opencode.list_sessions() == []


def test_malformed_database_is_skipped_with_warning(session_client, caplog):
    client, data, _ = session_client
    make_database(data, malformed=True)
    with caplog.at_level(logging.WARNING):
        assert all(row["source"] != "opencode" for row in client.get("/api/sessions").json())
    assert "opencode" in caplog.text.lower()


def test_opencode_database_is_never_written(session_client):
    client, data, _ = session_client
    path = make_database(data)
    before = {item.name: (item.stat().st_mtime_ns, item.stat().st_size) for item in data.iterdir()}
    assert client.get("/api/sessions").status_code == 200
    assert client.get("/api/sessions/opencode:session-one").status_code == 200
    assert client.post("/api/sessions/opencode:session-one/save-to-memory").status_code == 200
    after = {item.name: (item.stat().st_mtime_ns, item.stat().st_size) for item in data.iterdir()}
    assert before == after
    assert path.name in after


def test_locked_database_returns_no_opencode_rows(session_client, caplog):
    client, data, _ = session_client
    path = make_database(data)
    lock = sqlite3.connect(path, timeout=0.1)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        with caplog.at_level(logging.WARNING):
            rows = client.get("/api/sessions").json()
        assert all(row.get("source") != "opencode" for row in rows)
        assert "opencode" in caplog.text.lower()
    finally:
        lock.rollback()
        lock.close()
