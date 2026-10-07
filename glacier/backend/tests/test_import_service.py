import io
import json
import os
import zipfile

import pytest

import import_service
import vault


def _chatgpt_export(text="Question", answer="Answer"):
    data = [{
        "id": "gpt-1", "title": "A conversation", "create_time": 1700000000,
        "current_node": "a1", "mapping": {
            "u1": {"parent": None, "message": {"author": {"role": "user"}, "content": {"parts": [text]}}},
            "a1": {"parent": "u1", "message": {"author": {"role": "assistant"}, "content": {"parts": [answer]}}},
        },
    }]
    return json.dumps(data).encode()


def _claude_export(text="Hello", answer="Hi"):
    return json.dumps([{
        "uuid": "claude-1", "name": "Claude conversation", "created_at": "2024-03-04T12:30:00Z",
        "chat_messages": [{"sender": "human", "text": text}, {"sender": "assistant", "text": answer}],
    }]).encode()


def _zip(entries):
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return content.getvalue()


@pytest.fixture
def setup_imports(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("GLACIER_HOME", str(home))
    monkeypatch.setenv("GLACIER_IMPORT_DIR", str(tmp_path / "watched"))
    vault.init(str(home / "vault"))
    return home


def test_imports_both_formats_and_repeat_is_unchanged(setup_imports):
    gpt = _zip({"conversations.json": _chatgpt_export()})
    claude = _zip({"conversations.json": _claude_export()})
    assert import_service.import_export("chatgpt", upload=io.BytesIO(gpt), filename="gpt.zip") == {"added": 1, "updated": 0, "unchanged": 0}
    assert import_service.import_export("claude", upload=io.BytesIO(claude), filename="claude.zip") == {"added": 1, "updated": 0, "unchanged": 0}
    assert import_service.import_export("chatgpt", upload=io.BytesIO(gpt), filename="gpt.zip") == {"added": 0, "updated": 0, "unchanged": 1}
    assert "author: glacier-import" in vault.read_raw_note("imports/chatgpt/2023-11-14-a-conversation.md")


def test_changed_conversation_updates_existing_note(setup_imports):
    import_service.import_export("chatgpt", upload=io.BytesIO(_zip({"conversations.json": _chatgpt_export()})), filename="gpt.zip")
    result = import_service.import_export("chatgpt", upload=io.BytesIO(_zip({"conversations.json": _chatgpt_export(answer="Changed answer")})), filename="gpt.zip")
    assert result == {"added": 0, "updated": 1, "unchanged": 0}
    assert "Changed answer" in vault.read_raw_note("imports/chatgpt/2023-11-14-a-conversation.md")


def test_refresh_uses_newest_export_in_watched_folder(setup_imports, monkeypatch):
    watched = setup_imports.parent / "watched"
    watched.mkdir()
    older = watched / "old.zip"
    newer = watched / "new.zip"
    older.write_bytes(_zip({"conversations.json": _chatgpt_export(answer="Old")}))
    newer.write_bytes(_zip({"conversations.json": _chatgpt_export(answer="Newest")}))
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    assert import_service.refresh() == {"chatgpt": {"added": 1, "updated": 0, "unchanged": 0}}
    assert "Newest" in vault.read_raw_note("imports/chatgpt/2023-11-14-a-conversation.md")


def test_rejects_zip_with_excessive_uncompressed_size(setup_imports, monkeypatch):
    monkeypatch.setattr(import_service, "MAX_UNCOMPRESSED_BYTES", 100)
    bomb = _zip({"conversations.json": b"x" * 1000})
    with pytest.raises(ValueError, match="too large"):
        import_service.import_export("chatgpt", upload=io.BytesIO(bomb), filename="gpt.zip")


def test_rejects_archive_with_too_many_files(setup_imports, monkeypatch):
    monkeypatch.setattr(import_service, "MAX_ARCHIVE_FILES", 1)
    archive = _zip({"conversations.json": _chatgpt_export(), "other.txt": b"x"})
    with pytest.raises(ValueError, match="too many files"):
        import_service.import_export("chatgpt", upload=io.BytesIO(archive), filename="gpt.zip")


def test_same_title_and_day_conversations_keep_distinct_notes(setup_imports):
    chats = [{
        "id": cid, "title": "Same title", "create_time": 1700000000,
        "mapping": {},
    } for cid in ("first-id", "second-id")]
    export = setup_imports / "same.json"
    export.write_text(json.dumps(chats))
    assert import_service.import_export("chatgpt", export) == {"added": 2, "updated": 0, "unchanged": 0}
    paths = vault.list_notes(".md", "imports/chatgpt")
    assert len(paths) == 2
    assert {import_service._field(vault.read_raw_note(path), "source_id") for path in paths} == {"first-id", "second-id"}


def test_refresh_source_detection_obeys_uncompressed_cap(setup_imports, monkeypatch):
    path = setup_imports / "large.zip"
    path.write_bytes(_zip({"conversations.json": _chatgpt_export()}))
    monkeypatch.setattr(import_service, "MAX_UNCOMPRESSED_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        import_service._source_in(path)


def test_path_variant_accepts_only_zip_or_json(setup_imports):
    path = setup_imports / "export.txt"
    path.write_text("[]")
    with pytest.raises(ValueError, match="ZIP or JSON"):
        import_service.import_export("chatgpt", path)


def test_upload_body_reader_uses_one_gib_cap(monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request
    from routes.files import _read_bounded_body
    import asyncio

    consumed = []
    async def receive():
        consumed.append(True)
        return {"type": "http.request", "body": b"x" * (64 * 1024 + 51), "more_body": False}

    scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST", "path": "/api/imports",
             "raw_path": b"/api/imports", "query_string": b"", "headers": [], "server": ("test", 80),
             "client": ("test", 1), "scheme": "http"}
    request = Request(scope, receive)
    monkeypatch.setattr("routes.files.files_store.max_upload_bytes", lambda: 50)
    with pytest.raises(HTTPException) as error:
        asyncio.run(_read_bounded_body(request))
    assert error.value.status_code == 413
    assert len(consumed) == 1
