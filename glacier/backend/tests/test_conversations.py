"""Acceptance tests for saved Ask conversation history."""
import os
import sys
import textwrap
import time
import uuid

import httpx

from conftest import Server


def _conversation_server(tmp_path, monkeypatch):
    script = tmp_path / "chat.py"
    script.write_text(textwrap.dedent('''
        import json, sys
        args = sys.argv[1:]
        out = args[args.index("-o") + 1]
        prompt = args[-1]
        with open(out, "w", encoding="utf-8") as result:
            json.dump({"reply": "Reply to " + prompt, "automation": False}, result)
    '''), encoding="utf-8")
    command = script
    if os.name != "nt":
        command = tmp_path / "chat.sh"
        command.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        command.chmod(0o755)
    monkeypatch.setenv("GLACIER_CHAT_BIN", str(command))
    monkeypatch.setenv("GLACIER_ASK_ROUTE", "codex")
    home = tmp_path / "home"
    home.mkdir()
    return Server(home).start()


def _chat(server, conversation_id, message):
    return httpx.post(server.url + "/api/assistant/chat",
                      json={"conversation_id": conversation_id, "message": message}, timeout=30)


def test_conversations_list_detail_order_default_title_and_search(tmp_path, monkeypatch):
    server = _conversation_server(tmp_path, monkeypatch)
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    question = ("Find the ORCHID schedule " + "with more details " * 6).rstrip()
    shortened_question = " ".join(question.split())[:60].rstrip()
    try:
        assert _chat(server, first, question).status_code == 200
        time.sleep(0.02)
        assert _chat(server, second, "Review the BLUEBIRD report").status_code == 200

        rows = server.get("/api/assistant/conversations")
        assert [row["id"] for row in rows] == [second, first]
        assert rows[1]["title"] == shortened_question
        assert len(rows[1]["title"]) == 60
        assert rows[1]["messages"] == 2
        detail = server.get(f"/api/assistant/conversations/{first}")
        assert detail["id"] == first
        assert detail["title"] == shortened_question
        assert detail["messages"][0]["who"] == "you"
        assert detail["messages"][0]["text"] == question
        assert detail["messages"][1]["who"] == "glacier"
        assert detail["messages"][1]["text"] == "Reply to " + question
        assert detail["messages"][0]["at"]

        matches = server.get("/api/assistant/conversations?q=orchid")
        assert [row["id"] for row in matches] == [first]
        matches = server.get("/api/assistant/conversations?q=bluebird")
        assert [row["id"] for row in matches] == [second]
        matches = server.get("/api/assistant/conversations?q=REPLY")
        assert [row["id"] for row in matches] == [second, first]
    finally:
        server.stop()


def test_rename_persists_across_append_and_is_undoable(tmp_path, monkeypatch):
    server = _conversation_server(tmp_path, monkeypatch)
    conversation_id = str(uuid.uuid4())
    path = f"conversations/{conversation_id}.md"
    try:
        assert _chat(server, conversation_id, "First question").status_code == 200
        renamed = httpx.post(server.url + f"/api/assistant/conversations/{conversation_id}/rename",
                             json={"title": "My saved topic"}, timeout=30)
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "My saved topic"
        assert _chat(server, conversation_id, "A follow up").status_code == 200
        detail = server.get(f"/api/assistant/conversations/{conversation_id}")
        assert detail["title"] == "My saved topic"
        assert len(detail["messages"]) == 4
        note = server.get("/api/memory/note", params={"path": path})
        assert note["meta"]["title"] == "My saved topic"
        with open(os.path.join(server.home, "vault", path), encoding="utf-8") as saved_note:
            assert 'title: "My saved topic"' in saved_note.read()

        undo_append = httpx.post(server.url + "/api/memory/undo", json={"path": path}, timeout=30)
        assert undo_append.status_code == 200
        undo = httpx.post(server.url + "/api/memory/undo", json={"path": path, "commit": renamed.json()["commit"]}, timeout=30)
        assert undo.status_code == 200
        assert server.get(f"/api/assistant/conversations/{conversation_id}")["title"] == "First question"
    finally:
        server.stop()


def test_bad_id_missing_note_invalid_rename_and_edited_markdown_are_safe(tmp_path, monkeypatch):
    server = _conversation_server(tmp_path, monkeypatch)
    try:
        invalid = httpx.get(server.url + "/api/assistant/conversations/not-a-uuid", timeout=30)
        assert invalid.status_code == 400
        missing_id = str(uuid.uuid4())
        missing = httpx.get(server.url + f"/api/assistant/conversations/{missing_id}", timeout=30)
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Conversation not found"
        for title in ("", "  ", "x" * 81, "two\nlines"):
            response = httpx.post(server.url + f"/api/assistant/conversations/{missing_id}/rename",
                                  json={"title": title}, timeout=30)
            assert response.status_code == 400

        edited_id = str(uuid.uuid4())
        write = httpx.put(server.url + "/api/memory/note", json={
            "path": f"conversations/{edited_id}.md",
            "body": "# Conversation edited\n\nnot a recognized section\n\n## ???\n\n**Someone else:** odd text\n",
            "author": "owner",
        }, timeout=30)
        assert write.status_code == 200
        listed = server.get("/api/assistant/conversations")
        assert any(row["id"] == edited_id for row in listed)
        detail = server.get(f"/api/assistant/conversations/{edited_id}")
        assert detail["messages"] == []
    finally:
        server.stop()


def test_bad_rename_title_is_plain_400(tmp_path, monkeypatch):
    server = _conversation_server(tmp_path, monkeypatch)
    try:
        response = httpx.post(server.url + f"/api/assistant/conversations/{uuid.uuid4()}/rename",
                              json={"title": "line\nbreak"}, timeout=30)
        assert response.status_code == 400
        assert response.json()["detail"] == "Title must be 1 to 80 characters with no line breaks"
    finally:
        server.stop()
