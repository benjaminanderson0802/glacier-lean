import json
import shutil
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
def mirror_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    source = tmp_path / "codex-sessions"
    fixture_dir = __file__.replace("test_session_mirror.py", "fixtures/codex_sessions")
    shutil.copytree(fixture_dir, source)
    monkeypatch.setenv("GLACIER_CODEX_SESSIONS", str(source))
    keyring.set_keyring(MemoryKeyring())
    vault.init(str(tmp_path / "vault"))
    app = FastAPI()
    app.include_router(sessions.router)
    return TestClient(app), source, tmp_path


def test_lists_and_reads_nested_codex_sessions_with_unknown_and_bad_lines(mirror_client, caplog):
    client, _, _ = mirror_client
    rows = client.get("/api/sessions").json()
    assert {row["id"] for row in rows} == {"session-one", "session-two"}
    first = next(row for row in rows if row["id"] == "session-one")
    assert first == {
        "id": "session-one", "tool": "codex", "started": "2020-10-07T10:00:00+00:00",
        "updated": "2020-10-07T10:00:06+00:00", "title": "Please fix the parser bug",
        "cwd": "/work/project", "active": False,
    }
    events = client.get("/api/sessions/session-one").json()["events"]
    assert [event["type"] for event in events] == [
        "user_message", "assistant_message", "command", "command_output", "file_change", "other",
    ]
    assert events[0]["text"] == "Please fix the parser bug"
    assert "pytest -q" in events[2]["text"]
    assert "parser.py" in events[4]["text"]
    assert events[-1]["text"] == "custom_future_event"
    assert "malformed" in caplog.text.lower()


def test_active_is_based_on_recent_event_and_old_sessions_are_inactive(mirror_client):
    client, source, _ = mirror_client
    path = source / "2026/10/07/session-two.jsonl"
    lines = path.read_text().splitlines()
    lines[-1] = json.dumps({"type": "event_msg", "timestamp": datetime.now(timezone.utc).isoformat(),
                            "payload": {"type": "agent_message", "message": "Working"}})
    path.write_text("\n".join(lines) + "\n")
    rows = {row["id"]: row for row in client.get("/api/sessions").json()}
    assert rows["session-two"]["active"] is True
    assert rows["session-one"]["active"] is False


def test_save_to_memory_redacts_secrets_and_is_idempotent_per_version(mirror_client):
    client, source, home = mirror_client
    keyring.set_password(secrets_store.SERVICE, "session-token", "codex-secret-value")
    secrets_store._write_names(["session-token"])
    path = source / "2026/10/07/session-one.jsonl"
    with path.open("a") as handle:
        handle.write(json.dumps({"type": "event_msg", "timestamp": "2026-10-07T10:00:07Z",
                                "payload": {"type": "agent_message", "message": "Used codex-secret-value safely."}}) + "\n")

    response = client.post("/api/sessions/session-one/save-to-memory")
    assert response.status_code == 200
    saved = response.json()
    assert saved["path"].startswith("sessions/")
    note = (home / "vault" / saved["path"]).read_text()
    assert "author: glacier-mirror" in note
    assert "[secret session-token]" in note
    assert "codex-secret-value" not in note
    again = client.post("/api/sessions/session-one/save-to-memory")
    assert again.status_code == 200
    assert again.json() == {"saved": False, "path": saved["path"]}

    with path.open("a") as handle:
        handle.write(json.dumps({"type": "event_msg", "timestamp": "2026-10-07T10:00:08Z",
                                "payload": {"type": "agent_message", "message": "New version."}}) + "\n")
    revised = client.post("/api/sessions/session-one/save-to-memory")
    assert revised.json()["saved"] is True
    assert len(list((home / "vault" / "sessions").glob("*.md"))) == 2


def test_missing_session_is_not_found(mirror_client):
    client, _, _ = mirror_client
    assert client.get("/api/sessions/missing").status_code == 404
