import os
import sys

import httpx
import pytest


BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def test_rename_rewrites_resolved_links_once_and_undo_restores_all(server):
    import git
    from pathlib import Path

    server.put("/api/memory/note", {
        "path": "imports/chatgpt/old-chat.md",
        "body": "---\ncustom: kept\n---\n\n# old-chat\n", "author": "owner",
    })
    server.put("/api/memory/note", {
        "path": "notes/links.md",
        "body": "[[imports/chatgpt/old-chat]] [[imports/chatgpt/old-chat|alias]] "
                "[[imports/chatgpt/old-chat#Heading]] ![[imports/chatgpt/old-chat]] "
                "[chat](../imports/chatgpt/old-chat.md) `[[old-chat]]`\n\n"
                "```md\n[[old-chat]] [x](../imports/chatgpt/old-chat.md)\n```\n",
        "author": "owner",
    })
    vault_path = Path(server.home) / "vault"
    repo = git.Repo(vault_path)
    before_links = (vault_path / "notes/links.md").read_text()
    before_count = len(list(repo.iter_commits()))
    previous = repo.git.log("-1", "--format=%h", "--", "imports/chatgpt/old-chat.md")

    result = server.post("/api/memory/rename", {"from": "imports/chatgpt/old-chat.md", "to": "chats/new-chat.md"})

    assert result["path"] == "chats/new-chat.md" and result["commit"]
    repo = git.Repo(vault_path)
    assert len(list(repo.iter_commits())) == before_count + 1
    raw = (vault_path / "chats/new-chat.md").read_text()
    assert 'title: "new-chat"' in raw
    assert "custom: kept" in raw and "# new-chat" in raw
    rewritten = (vault_path / "notes/links.md").read_text()
    assert "[[chats/new-chat]]" in rewritten
    assert "[[chats/new-chat|alias]]" in rewritten
    assert "[[chats/new-chat#Heading]]" in rewritten
    assert "![[chats/new-chat]]" in rewritten
    assert "[chat](../chats/new-chat.md)" in rewritten
    assert "`[[old-chat]]`" in rewritten
    assert "```md\n[[old-chat]] [x](../imports/chatgpt/old-chat.md)\n```" in rewritten
    assert repo.commit(previous).hexsha in [c.hexsha for c in repo.iter_commits()]

    # The memory undo endpoint uses the rename commit's parent tree to restore the
    # complete transaction, including the old name and every inbound link.
    undone = server.post("/api/memory/undo", {"path": "notes/links.md", "commit": result["commit"]})
    assert undone["path"] == "notes/links.md"
    assert (vault_path / "imports/chatgpt/old-chat.md").read_text()
    assert not (vault_path / "chats/new-chat.md").exists()
    assert (vault_path / "notes/links.md").read_text() == before_links


@pytest.mark.parametrize(("source", "target", "message"), [
    ("missing.md", "new.md", "That note could not be found"),
    ("note.md", "exists.md", "A note already exists at that path"),
    ("../escape.md", "safe.md", "That note path is not allowed"),
    ("note.md", "bad:name.md", "That note name is not allowed"),
    ("runs/run-a.md", "run-b.md", "Run notes can't be renamed from memory"),
    ("claims/a.md", "claim-b.md", "Claims can't be renamed from memory"),
])
def test_rename_refusals(server, source, target, message):
    if source == "note.md":
        server.put("/api/memory/note", {"path": source, "body": "# Note", "author": "owner"})
    if target == "exists.md":
        server.put("/api/memory/note", {"path": target, "body": "# Exists", "author": "owner"})
    response = httpx.post(server.url + "/api/memory/rename", json={"from": source, "to": target})
    expected = 404 if message == "That note could not be found" else 409 if message == "A note already exists at that path" else 400
    assert response.status_code == expected
    assert response.json()["detail"] == message


def test_rename_publishes_delete_create_and_updated_memory_events(server):
    import asyncio
    import websockets

    server.put("/api/memory/note", {"path": "old.md", "body": "# Old", "author": "owner"})
    server.put("/api/memory/note", {"path": "links.md", "body": "[[old]]", "author": "owner"})
    uri = server.url.replace("http://", "ws://") + "/api/events?token=glacier-test-token"

    async def collect():
        async with websockets.connect(uri) as socket:
            import asyncio
            await asyncio.to_thread(server.post, "/api/memory/rename", {"from": "old.md", "to": "folder/new.md"})
            events = []
            while len(events) < 3:
                event = await asyncio.wait_for(socket.recv(), timeout=3)
                import json
                data = json.loads(event)
                if data.get("type") == "memory":
                    events.append(data)
            return events

    events = asyncio.run(collect())
    assert {(event["path"], event["change"], event["author"]) for event in events} == {
        ("old.md", "deleted", "owner"),
        ("folder/new.md", "created", "owner"),
        ("links.md", "updated", "owner"),
    }


def test_undo_rename_leaves_other_unsaved_files_alone_and_refuses_when_old_name_is_taken(server):
    from pathlib import Path

    server.put("/api/memory/note", {"path": "a.md", "body": "# a\n", "author": "owner"})
    server.put("/api/memory/note", {"path": "links.md", "body": "see [[a]]\n", "author": "owner"})
    vault_path = Path(server.home) / "vault"
    first = server.post("/api/memory/rename", {"from": "a.md", "to": "b.md"})
    # A file edited in another editor and not yet saved by Glacier must survive an undo.
    (vault_path / "editing-elsewhere.md").write_text("# draft in another app\n", encoding="utf-8")
    undone = server.post("/api/memory/undo", {"path": "b.md", "commit": first["commit"]})
    assert undone["commit"]
    assert (vault_path / "a.md").exists() and not (vault_path / "b.md").exists()
    assert "[[a]]" in (vault_path / "links.md").read_text(encoding="utf-8")
    assert (vault_path / "editing-elsewhere.md").read_text(encoding="utf-8") == "# draft in another app\n"

    second = server.post("/api/memory/rename", {"from": "a.md", "to": "c.md"})
    server.put("/api/memory/note", {"path": "a.md", "body": "# a new note with the old name\n", "author": "owner"})
    response = httpx.post(server.url + "/api/memory/undo", json={"path": "c.md", "commit": second["commit"]}, timeout=30)
    assert response.status_code == 409
    assert "old name" in response.json()["detail"]
