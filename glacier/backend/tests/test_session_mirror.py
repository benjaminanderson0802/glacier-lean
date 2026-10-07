import json
import logging
import shutil
from datetime import datetime, timezone

import keyring
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import secrets_store
import session_mirror
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
def mirror_client(tmp_path, monkeypatch, request):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    source = tmp_path / "codex-sessions"
    fixture_dir = __file__.replace("test_session_mirror.py", "fixtures/codex_sessions")
    shutil.copytree(fixture_dir, source)
    monkeypatch.setenv("GLACIER_CODEX_SESSIONS", str(source))
    original_keyring = keyring.get_keyring()
    test_keyring = MemoryKeyring()
    keyring.set_keyring(test_keyring)
    def restore_keyring():
        keyring.set_keyring(original_keyring)
    request.addfinalizer(restore_keyring)
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
    assert events[-1]["text"] == '{"note": "preserve this"}'
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


def test_redacts_list_titles_and_detail_event_text(mirror_client):
    client, source, _ = mirror_client
    keyring.set_password(secrets_store.SERVICE, "session-token", "codex-secret-value")
    secrets_store._write_names(["session-token"])
    path = source / "2026/10/07/session-two.jsonl"
    path.write_text(path.read_text().replace("Review this config", "Review codex-secret-value"))

    rows = client.get("/api/sessions").json()
    assert next(row for row in rows if row["id"] == "session-two")["title"] == "Review [secret session-token]"
    detail = client.get("/api/sessions/session-two").json()
    assert "codex-secret-value" not in detail["events"][0]["text"]


def test_detail_caps_to_newest_2000_events_and_filters_digest(mirror_client):
    client, source, _ = mirror_client
    path = source / "2026/10/07/session-two.jsonl"
    with path.open("a") as handle:
        for index in range(2005):
            handle.write(json.dumps({"type": "event_msg", "timestamp": "2026-10-07T09:00:03Z",
                                     "payload": {"type": "agent_message", "message": f"event-{index}"}}) + "\n")

    detail = client.get("/api/sessions/session-two").json()
    assert detail["truncated"] is True
    assert len(detail["events"]) == 2000
    assert detail["events"][0]["text"] == "event-5"
    assert detail["events"][-1]["text"] == "event-2004"


def test_overlong_jsonl_line_is_skipped_with_warning(mirror_client, caplog):
    client, source, _ = mirror_client
    path = source / "2026/10/07/session-two.jsonl"
    with path.open("a") as handle:
        handle.write('{"type":"event_msg","payload":{"type":"agent_message","message":"' + "x" * 1_000_001 + '"}}\n')

    with caplog.at_level(logging.WARNING):
        detail = client.get("/api/sessions/session-two").json()
    assert all("x" * 100 not in event["text"] for event in detail["events"])
    assert "over-long" in caplog.text.lower()


def test_saved_note_filename_sanitizes_session_id(mirror_client):
    client, source, _ = mirror_client
    path = source / "2026/10/07/session-two.jsonl"
    lines = path.read_text().splitlines()
    lines[0] = json.dumps({"type": "session_meta", "payload": {"id": "CON.txt", "cwd": "/work", "timestamp": "2026-10-07T09:00:00Z"}})
    path.write_text("\n".join(lines) + "\n")

    response = client.post("/api/sessions/CON.txt/save-to-memory")
    assert response.status_code == 200
    assert response.json()["path"].startswith("sessions/session-CON.txt-")


def test_metadata_is_read_only_from_first_line_and_list_cache_reuses_summaries(mirror_client, monkeypatch):
    client, source, _ = mirror_client
    path = source / "2026/10/07/session-two.jsonl"
    lines = path.read_text().splitlines()
    metadata = json.dumps({"type": "session_meta", "payload": {"id": "metadata-only-id", "cwd": "/ignored", "timestamp": "2026-10-07T09:00:00Z"}})
    lines.pop(0)
    path.write_text("\n".join(lines + [metadata]) + "\n")

    rows = client.get("/api/sessions").json()
    assert "metadata-only-id" not in {row["id"] for row in rows}
    assert path.stem in {row["id"] for row in rows}

    calls = 0
    original = session_mirror._records

    def count_reads(file_path, warnings=True):
        nonlocal calls
        calls += 1
        yield from original(file_path, warnings)

    monkeypatch.setattr(session_mirror, "_records", count_reads)
    session_mirror._LIST_CACHE.clear()
    session_mirror.list_sessions()
    initial_calls = calls
    session_mirror.list_sessions()
    assert calls == initial_calls


def test_missing_session_is_not_found(mirror_client):
    client, _, _ = mirror_client
    assert client.get("/api/sessions/missing").status_code == 404
