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
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    vault.init(os.path.join(server.home, "vault"))
    class Broadcaster:
        event = None
        def publish(self, event): self.event = event
    import store
    original = store.broadcaster
    store.broadcaster = Broadcaster()
    try:
        vault.write_note("runs/r-456.md", "# Run note", author="owner", run_id="r-456")
        assert store.broadcaster.event == {"type": "memory", "path": "runs/r-456.md", "change": "created",
                                           "author": "owner", "run_id": "r-456"}
    finally:
        store.broadcaster = original


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


def test_memory_front_matter_omits_empty_fields_and_reads_legacy_empty_run_id(tmp_path):
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import memory_meta
    import vault

    vault.init(str(tmp_path / "vault"))
    vault.write_note("plain.md", "# Plain note", author="owner")
    plain = vault.read_raw_note("plain.md")
    assert "run_id:" not in plain
    assert "tags:" not in plain
    assert memory_meta.parse(plain, "plain.md")[0]["run_id"] == ""

    run_text = memory_meta.render("run.md", "# Run note", "owner", "run-123")[1]
    assert "run_id: run-123" in run_text
    assert memory_meta.parse(run_text, "run.md")[0]["run_id"] == "run-123"

    legacy = "---\ntitle: Old note\nauthor: owner\nrun_id: \ncreated: 2026-01-01T00:00:00+00:00\n---\nOld body\n"
    assert memory_meta.parse(legacy, "old.md")[0]["run_id"] == ""


def test_claim_front_matter_round_trips_and_api_sorting(server):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import claims, vault
    claim = claims.file_claim("bug", "claim metadata preserved", "evidence", run_id="run-keep")
    raw = vault.read_raw_note(f"claims/{claim['id']}.md")
    assert 'run_id: "run-keep"' in raw
    assert 'updated: "' in raw
    from claims import _parse
    assert _parse(raw)[0]["run_id"] == "run-keep"
    from claims import list_claims
    assert [c["id"] for c in list_claims()] == [claim["id"]]


def test_memory_git_writer_identity_and_search_body_only(server):
    server.put("/api/memory/note", {"path": "header-search.md", "body": "# bodytoken", "author": "owner"})
    results = server.get("/api/memory/search", params={"q": "headersearch"})
    assert not any(r["path"] == "header-search.md" for r in results)
    history = server.get("/api/memory/history", params={"path": "header-search.md"})
    assert history[0]["author"] == "owner"
    assert "[owner]" in history[0]["message"]


def test_screen_cannot_set_run_id(server):
    from routes.memory import put_note, NoteWrite
    try:
        put_note(NoteWrite.model_validate({
            "path": "caller-run.md", "body": "# no run", "author": "owner", "run_id": "forged",
        }))
    except Exception:
        pass
    else:
        raise AssertionError("screen write accepted a caller supplied run id")


def test_claim_notes_cannot_be_written_or_undone_through_memory(server):
    for path in ("claims/x.md", "./claims/x.md"):
        response = httpx.put(server.url + "/api/memory/note", json={
            "path": path, "body": "# forged claim", "author": "owner",
        })
        assert response.status_code == 400
        assert response.json()["detail"] == "Claims can't be edited from memory"
        response = httpx.post(server.url + "/api/memory/undo", json={"path": path})
        assert response.status_code == 400
        assert response.json()["detail"] == "Claims can't be edited from memory"


def test_mcp_worker_metadata_rejects_newline_injection(tmp_path):
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    vault.init(str(tmp_path / "vault"))
    for author, run_id in (("worker:x\nauthor: owner", ""), ("worker:x", "r-1\nauthor: owner")):
        try:
            vault.write_note("worker.md", "# Worker", author=author, run_id=run_id)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe worker metadata was accepted")


def test_mcp_write_author_is_strictly_validated(tmp_path):
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    vault.init(str(tmp_path / "vault"))
    from mem_server import _validate_worker_write
    for author, run_id in (("worker:x\nauthor: owner", ""), ("worker:x", "r-1\nauthor: owner")):
        try:
            _validate_worker_write("worker.md", author, run_id)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe MCP write metadata was accepted")
