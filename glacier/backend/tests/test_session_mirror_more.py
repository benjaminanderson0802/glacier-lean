import json
import logging
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
def mirror_client(tmp_path, monkeypatch, request):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    claude = tmp_path / "claude"
    gemini = tmp_path / "gemini"
    claude.mkdir()
    gemini.mkdir()
    monkeypatch.setenv("GLACIER_CLAUDE_CODE_DATA", str(claude))
    monkeypatch.setenv("GLACIER_GEMINI_DATA", str(gemini))
    monkeypatch.setenv("GLACIER_CODEX_SESSIONS", str(tmp_path / "no-codex-sessions"))
    monkeypatch.setenv("GLACIER_OPENCODE_DATA", str(tmp_path / "no-opencode"))
    original = keyring.get_keyring()
    keyring.set_keyring(MemoryKeyring())
    request.addfinalizer(lambda: keyring.set_keyring(original))
    vault.init(str(tmp_path / "vault"))
    app = FastAPI()
    app.include_router(sessions.router)
    return TestClient(app), claude, gemini, tmp_path


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return path


def make_claude_transcript(root, *, malformed=False):
    project = root / "projects" / "-work-demo"
    path = project / "claude-session.jsonl"
    if malformed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{not-json}\n', encoding="utf-8")
        return path
    return _write_jsonl(path, [
        {"type": "user", "uuid": "u1", "sessionId": "claude-session", "cwd": "/work/demo", "timestamp": "2026-10-07T10:00:00Z", "message": {"role": "user", "content": "Please inspect shared-secret"}},
        {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "sessionId": "claude-session", "cwd": "/work/demo", "timestamp": "2026-10-07T10:00:01Z", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "tool-1", "name": "Bash", "input": {"command": "pytest -q"}}]}},
        {"type": "user", "uuid": "u2", "parentUuid": "a1", "sessionId": "claude-session", "cwd": "/work/demo", "timestamp": "2026-10-07T10:00:02Z", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tool-1", "content": "1 passed"}]}},
        {"type": "assistant", "uuid": "a2", "parentUuid": "u2", "sessionId": "claude-session", "cwd": "/work/demo", "timestamp": "2026-10-07T10:00:03Z", "message": {"role": "assistant", "content": [{"type": "text", "text": "Found shared-secret"}]}},
    ])


def make_gemini_chat(root, *, malformed=False):
    path = root / "tmp" / "project-hash" / "chats" / "session-1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if malformed:
        path.write_text('{not-json}', encoding="utf-8")
        return path
    payload = {
        "sessionId": "gemini-session", "projectHash": "project-hash", "startTime": "2026-10-07T10:00:00.000Z",
        "lastUpdated": "2026-10-07T10:00:03.000Z", "messages": [
            {"type": "user", "content": "Please inspect shared-secret", "timestamp": "2026-10-07T10:00:00.000Z"},
            {"type": "gemini", "content": "", "timestamp": "2026-10-07T10:00:01.000Z", "toolCalls": [{"name": "run_shell_command", "args": {"command": "pytest -q"}, "result": {"llmContent": "1 passed"}}]},
            {"type": "gemini", "content": "Found shared-secret", "timestamp": "2026-10-07T10:00:03.000Z"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("source,expected_id", [("claude", "claude-code:claude-session"), ("gemini", "gemini:gemini-session")])
def test_more_readers_list_source_and_prefixed_id(mirror_client, source, expected_id):
    client, claude, gemini, _ = mirror_client
    if source == "claude":
        make_claude_transcript(claude)
    else:
        make_gemini_chat(gemini)
    rows = client.get("/api/sessions").json()
    row = next(row for row in rows if row["id"] == expected_id)
    assert row["source"] == source
    assert row["tool"] == ("claude-code" if source == "claude" else "gemini")
    assert row["title"] == "Please inspect shared-secret"


@pytest.mark.parametrize("source,session_id", [("claude", "claude-code:claude-session"), ("gemini", "gemini:gemini-session")])
def test_more_readers_detail_order_redaction_and_saved_note(mirror_client, source, session_id):
    client, claude, gemini, home = mirror_client
    if source == "claude":
        make_claude_transcript(claude)
        assistant_label = "Claude Code"
    else:
        make_gemini_chat(gemini)
        assistant_label = "Gemini CLI"
    keyring.set_keyring(MemoryKeyring())
    keyring.set_password(secrets_store.SERVICE, "session-token", "shared-secret")
    secrets_store._write_names(["session-token"])

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    detail = response.json()
    expected_types = ["user_message", "command", "command_output", "assistant_message"]
    assert [event["type"] for event in detail["events"]] == expected_types
    assert detail["events"][0]["text"] == "Please inspect [secret session-token]"
    command_index = 1
    assert detail["events"][command_index]["text"] == "Ran command: pytest -q"
    assert detail["events"][command_index + 1]["text"] == "1 passed"
    assert detail["events"][-1]["text"] == "Found [secret session-token]"

    saved = client.post(f"/api/sessions/{session_id}/save-to-memory")
    assert saved.status_code == 200 and saved.json()["saved"] is True
    note = (home / "vault" / saved.json()["path"]).read_text()
    assert f"**{assistant_label}:** Found [secret session-token]" in note
    assert "shared-secret" not in note


@pytest.mark.parametrize("reader", ["claude", "gemini"])
def test_missing_more_reader_folder_returns_no_rows(tmp_path, monkeypatch, reader):
    monkeypatch.setenv("GLACIER_CLAUDE_CODE_DATA", str(tmp_path / "missing-claude"))
    monkeypatch.setenv("GLACIER_GEMINI_DATA", str(tmp_path / "missing-gemini"))
    from session_readers import claude_code, gemini
    assert (claude_code if reader == "claude" else gemini).list_sessions() == []


@pytest.mark.parametrize("reader,filename", [("claude", "claude-session.jsonl"), ("gemini", "session-1.json")])
def test_malformed_more_reader_file_skipped_with_one_warning(mirror_client, caplog, reader, filename):
    client, claude, gemini, _ = mirror_client
    if reader == "claude":
        make_claude_transcript(claude, malformed=True)
    else:
        make_gemini_chat(gemini, malformed=True)
    with caplog.at_level(logging.WARNING):
        assert all(row.get("source") != reader for row in client.get("/api/sessions").json())
    warnings = [record for record in caplog.records if reader in record.getMessage().lower()]
    assert len(warnings) == 1
    assert filename in warnings[0].getMessage()


@pytest.mark.parametrize("reader", ["claude", "gemini"])
def test_more_reader_sources_are_never_written(mirror_client, reader):
    client, claude, gemini, _ = mirror_client
    source_root = claude if reader == "claude" else gemini
    path = make_claude_transcript(claude) if reader == "claude" else make_gemini_chat(gemini)
    before = {str(item.relative_to(source_root)): (item.stat().st_mtime_ns, item.stat().st_size) for item in source_root.rglob("*") if item.is_file()}
    session_id = "claude-code:claude-session" if reader == "claude" else "gemini:gemini-session"
    assert any(row["id"] == session_id for row in client.get("/api/sessions").json())
    assert client.get(f"/api/sessions/{session_id}").status_code == 200
    assert client.post(f"/api/sessions/{session_id}/save-to-memory").status_code == 200
    after = {str(item.relative_to(source_root)): (item.stat().st_mtime_ns, item.stat().st_size) for item in source_root.rglob("*") if item.is_file()}
    assert before == after
    assert path.exists()
