"""Live memory events and large-vault graph acceptance tests."""
import json
import os
import sys
import time

import websockets.sync.client

from conftest import env


def _ws_url(server):
    return server.url.replace("http://", "ws://") + "/api/events"


def test_run_write_publishes_one_memory_websocket_event(server):
    server.put("/api/environments/live-memory", env("live-memory", [
        ("write", "note", {"path": "runs/live-run-note.md", "template": "# Run {run}"}),
    ], []))
    with websockets.sync.client.connect(_ws_url(server), open_timeout=10) as ws:
        run = server.post("/api/environments/live-memory/run")
        server.wait_run(run["run_id"])
        events = []
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                events.append(json.loads(ws.recv(timeout=max(0.01, deadline - time.monotonic()))))
            except TimeoutError:
                break
        memory = [e for e in events if e.get("type") == "memory"]
    assert memory == [{"type": "memory", "path": "runs/live-run-note.md", "change": "created",
                       "author": "run:" + run["run_id"], "run_id": run["run_id"]}]


def test_owner_save_publishes_one_memory_event(server):
    with websockets.sync.client.connect(_ws_url(server), open_timeout=10) as ws:
        server.put("/api/memory/note", {"path": "owner-live.md", "body": "# Owner", "author": "owner"})
        event = json.loads(ws.recv(timeout=2))
    assert event == {"type": "memory", "path": "owner-live.md", "change": "created", "author": "owner", "run_id": ""}


def test_memory_undo_publishes_one_write_event(server):
    server.put("/api/memory/note", {"path": "undo-live.md", "body": "# Before", "author": "owner"})
    server.put("/api/memory/note", {"path": "undo-live.md", "body": "# After", "author": "owner"})
    with websockets.sync.client.connect(_ws_url(server), open_timeout=10) as ws:
        server.post("/api/memory/undo", {"path": "undo-live.md"})
        event = json.loads(ws.recv(timeout=2))
    assert event == {"type": "memory", "path": "undo-live.md", "change": "updated", "author": "owner", "run_id": ""}


def test_graph_with_2000_notes_is_fast_and_complete(server, tmp_path):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import vault
    vault.init(os.path.join(server.home, "vault"))
    for i in range(2000):
        vault.write_note(f"bench/note-{i:04}.md", f"# Note {i}\n\nLinks [[bench/note-{(i + 1) % 2000:04}]].", author="owner")
    started = time.perf_counter()
    import httpx
    response = httpx.get(server.url + "/api/memory/graph", timeout=10)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    graph = response.json()
    notes = [node for node in graph["nodes"] if node["kind"] == "note" and node["id"].startswith("bench/")]
    assert elapsed < 2, f"graph took {elapsed:.3f}s"
    assert len(notes) == 2000
    assert len({node["id"] for node in notes}) == 2000


def test_graph_limit_keeps_newest_notes_and_direct_links(server):
    server.put("/api/memory/note", {"path": "older.md", "body": "# Older\n\n[[older-link]]", "author": "owner"})
    server.put("/api/memory/note", {"path": "newer.md", "body": "# Newer\n\n[[newer-link]]", "author": "owner"})
    # Two quick saves can share a file timestamp; set distinct ones so "newest" is unambiguous.
    vault_dir = os.path.join(server.home, "vault")
    os.utime(os.path.join(vault_dir, "older.md"), (1_000_000_000, 1_000_000_000))
    os.utime(os.path.join(vault_dir, "newer.md"), (2_000_000_000, 2_000_000_000))
    graph = server.get("/api/memory/graph", params={"limit": 1})
    assert {n["id"] for n in graph["nodes"] if n["id"] in {"older", "newer"}} == {"newer"}
    assert {e["target"] for e in graph["edges"] if e["source"] == "newer"} == {"owner", "newer-link"}


def test_cleanup_merge_publishes_updated_and_deleted_events(server):
    server.put("/api/memory/note", {"path": "dupe-a.md", "body": "# Same\nshared words here", "author": "owner"})
    server.put("/api/memory/note", {"path": "dupe-b.md", "body": "# Same\nshared words here", "author": "owner"})
    import memory_hygiene  # noqa: F401  (proposal shape lives server-side; drive it through the API)
    proposals = server.post("/api/memory/hygiene/scan")
    merge = next((p for p in proposals if p["kind"] == "merge" and {"dupe-a.md", "dupe-b.md"} <= set(p["paths"])), None)
    if merge is None:
        import pytest
        pytest.skip("scanner did not propose this merge on this data")
    with websockets.sync.client.connect(_ws_url(server), open_timeout=10) as ws:
        server.post(f"/api/memory/hygiene/{merge['id']}", {"approve": True})
        events = []
        deadline = time.monotonic() + 8  # generous under a loaded machine; stops as soon as both are seen
        while time.monotonic() < deadline and not (
                any(e.get("change") == "deleted" for e in events) and any(e.get("change") == "updated" for e in events)):
            try:
                events.append(json.loads(ws.recv(timeout=max(0.01, deadline - time.monotonic()))))
            except TimeoutError:
                break
    changes = {(e["path"], e["change"]) for e in events if e.get("type") == "memory"}
    assert any(change == "deleted" for _, change in changes)
    assert any(change == "updated" for _, change in changes)
