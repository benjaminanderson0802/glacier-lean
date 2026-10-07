import re

import asyncio
import httpx
import websockets


def test_memory_notes_metadata_links_search_history_undo_and_graph(server):
    first = server.put("/api/memory/note", {
        "path": "projects/alpha.md",
        "body": "# Alpha\n\nKeep the glacier keyword. #research\n\nSee [[projects/beta|Beta]] and [[runs/r-123]].",
        "author": "owner",
    })
    assert first["path"] == "projects/alpha.md" and first["commit"]
    note = server.get("/api/memory/note", params={"path": "projects/alpha.md"})
    assert note["meta"]["title"] == "Alpha"
    assert note["meta"]["author"] == "owner"
    assert note["meta"]["run_id"] == ""
    assert note["meta"]["created"] == note["meta"]["updated"]
    assert re.match(r"\d{4}-\d\d-\d\dT.*\+00:00$", note["meta"]["created"])
    assert note["meta"]["tags"] == ["research"]
    assert note["links_out"] == ["projects/beta", "runs/r-123"]

    second = server.put("/api/memory/note", {
        "path": "projects/beta.md", "body": "# Beta\n\nGlacier helper.", "author": "owner",
    })
    assert server.get("/api/memory/note", params={"path": "projects/beta.md"})["links_in"] == ["projects/alpha"]
    assert {n["id"] for n in server.get("/api/memory/graph")["nodes"]} >= {
        "projects/alpha", "projects/beta", "runs/r-123",
    }
    graph = server.get("/api/memory/graph")
    assert {tuple((e["source"], e["target"], e["kind"])) for e in graph["edges"]} >= {
        ("projects/alpha", "projects/beta", "link"),
        ("projects/alpha", "runs/r-123", "link"),
        ("projects/alpha", "owner", "wrote"),
    }

    notes = server.get("/api/memory/notes", params={"tag": "research", "author": "owner"})
    assert [n["path"] for n in notes] == ["projects/alpha.md"]
    assert server.get("/api/memory/search", params={"q": "glacier", "mode": "keyword"})[0]["path"] in {
        "projects/alpha.md", "projects/beta.md",
    }
    history = server.get("/api/memory/history", params={"path": "projects/beta.md"})
    assert history[0]["commit"] == second["commit"]
    assert {"author", "date", "message"} <= history[0].keys()

    server.put("/api/memory/note", {"path": "projects/beta.md", "body": "# Beta\n\nChanged text.", "author": "owner"})
    server.post("/api/memory/undo", {"path": "projects/beta.md"})
    assert "Glacier helper" in server.get("/api/memory/note", params={"path": "projects/beta.md"})["body"]


def test_memory_meaning_search_falls_back_to_keyword(server):
    server.put("/api/memory/note", {"path": "meaning.md", "body": "# Meaning\n\nA glacier fallback phrase.", "author": "owner"})
    result = server.get("/api/memory/search", params={"q": "glacier", "mode": "meaning"})
    assert result and result[0]["path"] == "meaning.md" and result[0]["fallback"] is True


def test_memory_write_metadata_and_event(server):
    async def check_event():
        async with websockets.connect(server.url.replace("http", "ws") + "/api/events") as ws:
            await asyncio.sleep(0.05)
            await asyncio.to_thread(httpx.put, server.url + "/api/memory/note", json={
                "path": "runs/r-456.md", "body": "# Run note", "author": "owner", "run_id": "r-456",
            })
            return await asyncio.wait_for(ws.recv(), timeout=2)
    import json
    event = json.loads(asyncio.run(check_event()))
    assert event == {"type": "memory", "path": "runs/r-456.md", "change": "created",
                     "author": "owner", "run_id": "r-456"}
    note = server.get("/api/memory/note", params={"path": "runs/r-456.md"})
    assert note["meta"]["author"] == "owner" and note["meta"]["run_id"] == "r-456"


def test_memory_path_traversal_and_non_owner_screen_write_are_refused(server):
    response = httpx.get(server.url + "/api/memory/note", params={"path": "../outside.md"})
    assert response.status_code == 400
    response = httpx.put(server.url + "/api/memory/note", json={
        "path": "bad.md", "body": "# Bad", "author": "worker:forged",
    })
    assert response.status_code == 400


def test_vault_worker_write_uses_service_metadata(tmp_path):
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    vault.init(str(tmp_path / "vault"))
    vault.write_note("worker.md", "# Worker note\n\n#agent", author="worker:tiny-model", run_id="r-9")
    text = vault.read_raw_note("worker.md")
    assert "author: worker:tiny-model" in text
    assert "run_id: r-9" in text
    assert "title: \"Worker note\"" in text
    assert "tags: [agent]" in text
    vault.write_note("runs/flow-123456abcdef.md", "Run 123456abcdef of flow", agent="glacier-runner")
    runner_text = vault.read_raw_note("runs/flow-123456abcdef.md")
    assert "author: run:123456abcdef" in runner_text
    assert "run_id: 123456abcdef" in runner_text
