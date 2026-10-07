import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone


def test_home_empty_state(server):
    body = server.get("/api/home")
    assert body["local_ai"]["online"] in (True, False, None)  # None = first probe still running
    assert body["local_ai"]["model"] is None or isinstance(body["local_ai"]["model"], str)
    assert body["counts"] == {"running": 0, "need_you": 0}
    assert body["needs_you"] == []
    assert body["running"] == []
    assert body["recent_notes"] == []


def _add_run(server, run_id, env_id, name, status, started_at, nodes, states):
    with sqlite3.connect(f"{server.home}/glacier.sqlite") as db:
        graph = {"id": env_id, "name": name, "nodes": [{"id": node, "type": "command", "config": {}}
                                                            for node in nodes]}
        db.execute("INSERT INTO glacier_runs VALUES (?, ?, ?, ?, ?, ?)",
                   (run_id, env_id, status, started_at, json.dumps(graph), "approval-node" if status == "waiting" else None))
        db.executemany("INSERT INTO glacier_nodes VALUES (?, ?, ?, NULL)",
                       [(run_id, node, state) for node, state in zip(nodes, states)])


def test_home_collects_each_need_you_kind_and_counts_steps(server):
    now = datetime.now(timezone.utc)
    stamp = lambda age: (now - timedelta(minutes=age)).isoformat()
    _add_run(server, "waiting-run", "approval-env", "Approval environment", "waiting", stamp(-1),
             ["a", "approval-node"], ["done", "waiting"])
    _add_run(server, "failed-run", "failed-env", "Failed environment", "failed", stamp(2), ["bad"], ["failed"])
    _add_run(server, "running-run", "running-env", "Running environment", "running", stamp(3),
             ["a", "b", "c", "d"], ["done", "done", "pending", "pending"])
    _add_run(server, "queued-run", "queued-env", "Queued environment", "queued", stamp(4), ["a"], ["pending"])
    with sqlite3.connect(f"{server.home}/glacier.sqlite") as db:
        db.execute("INSERT INTO glacier_runs VALUES (?, ?, ?, ?, ?, NULL)",
                   ("old-failure", "old", "failed", stamp(8 * 24 * 60), json.dumps({"name": "Old"})))

    claim_id = "2026-10-07-home-decision-a1b2c3"
    claim_file = f"{server.home}/vault/claims/{claim_id}.md"
    os.makedirs(os.path.dirname(claim_file), exist_ok=True)
    with open(claim_file, "w", encoding="utf-8") as stream:
        stream.write(f'---\nid: "{claim_id}"\nkind: "bug"\nsummary: "Needs a decision"\n'
                     f'status: "proposed"\nupdated: "{stamp(0)}"\nrun_id: ""\nnode_id: ""\n---\n')
    server.put("/api/memory/note", {"path": "recent.md", "body": "# Recent\nA saved note.", "author": "owner"})
    body = server.get("/api/home")

    assert body["local_ai"]["online"] in (True, False, None)  # None = first probe still running
    assert body["counts"] == {"running": 3, "need_you": 3}
    by_kind = {item["kind"]: item for item in body["needs_you"]}
    assert set(by_kind) == {"approval", "claim", "failed_run"}
    assert by_kind["approval"]["title"] == "approval waiting"
    assert by_kind["approval"]["detail"] == "Approval environment"
    assert by_kind["claim"]["ref"]["claim_id"] == claim_id
    assert by_kind["failed_run"]["ref"]["run_id"] == "failed-run"
    running = next(row for row in body["running"] if row["run_id"] == "running-run")
    assert (running["step"], running["steps"], running["name"]) == (2, 4, "Running environment")
    assert next(row for row in body["running"] if row["run_id"] == "queued-run")["status"] == "queued"
    assert body["recent_notes"][0]["path"] == "recent.md"
    assert body["recent_notes"][0]["summary"]


def test_home_orders_and_caps_needs_and_notes(server):
    now = datetime.now(timezone.utc)
    with sqlite3.connect(f"{server.home}/glacier.sqlite") as db:
        for i in range(25):
            started = (now - timedelta(minutes=i)).isoformat()
            run_id = f"waiting-{i:02}"
            graph = {"name": "Environment", "nodes": [{"id": "approval", "type": "approval", "config": {}}]}
            db.execute("INSERT INTO glacier_runs VALUES (?, ?, 'waiting', ?, ?, 'approval')",
                       (run_id, f"env-{i}", started, json.dumps(graph)))
            db.execute("INSERT INTO glacier_nodes VALUES (?, 'approval', 'waiting', NULL)", (run_id,))
    for i in range(12):
        server.put("/api/memory/note", {"path": f"notes/{i:02}.md", "body": f"# Note {i}\nSummary {i}", "author": "owner"})

    body = server.get("/api/home")
    assert len(body["needs_you"]) == 20
    assert body["needs_you"][0]["ref"]["run_id"] == "waiting-00"
    assert body["needs_you"][-1]["ref"]["run_id"] == "waiting-19"
    assert len(body["recent_notes"]) == 10
    assert body["recent_notes"][0]["path"] == "notes/11.md"
    assert body["recent_notes"][-1]["path"] == "notes/02.md"


def test_home_local_ai_becomes_known_after_first_probe(server):
    import time
    first = server.get("/api/home")["local_ai"]["online"]
    assert first in (True, False, None)
    deadline = time.monotonic() + 30
    online = first
    while online is None and time.monotonic() < deadline:
        time.sleep(0.5)
        online = server.get("/api/home")["local_ai"]["online"]
    assert isinstance(online, bool)


def test_home_recent_notes_scan_is_bounded_and_locked(server):
    for i in range(12):
        server.put("/api/memory/note", {"path": f"bulk/n{i}.md", "body": f"# N{i}\nline {i}", "author": "owner"})
    notes = server.get("/api/home")["recent_notes"]
    assert len(notes) == 10
    assert notes[0]["path"] == "bulk/n11.md"
