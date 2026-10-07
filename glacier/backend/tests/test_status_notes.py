import json
import sqlite3
from decimal import Decimal

import git
import vault


def _record_run(server, env_id, run_id, status, node_states, usage):
    db = sqlite3.connect(server.home + "/glacier.sqlite")
    graph = {"id": env_id, "name": "Weekly report", "nodes": [
        {"id": node_id, "type": "command", "config": {"command": "true"}}
        for node_id in node_states
    ], "edges": []}
    db.execute("INSERT INTO glacier_runs VALUES (?,?,?,?,?,NULL)",
               (run_id, env_id, status, "2026-10-07T12:00:00+00:00", json.dumps(graph)))
    for node_id, state in node_states.items():
        db.execute("INSERT INTO glacier_nodes VALUES (?,?,?,NULL)", (run_id, node_id, state))
    for node_id, row in usage.items():
        db.execute("INSERT INTO glacier_usage VALUES (?,?,?,?,?,?,?)",
                   (run_id, node_id, row["model"], row["route"], 11, 17, row["cost_usd"]))
    db.commit()
    db.close()


def test_status_note_rebuild_has_runs_failure_usage_and_exact_totals(server):
    server.put("/api/environments/monthly", {
        "id": "monthly", "name": "Monthly close", "nodes": [
            {"id": "prepare", "type": "command", "config": {}},
            {"id": "publish", "type": "command", "config": {}}
        ], "edges": []
    })
    _record_run(server, "monthly", "run-ok", "done", {"prepare": "done", "publish": "done"}, {
        "prepare": {"model": "model-a", "route": "local", "cost_usd": 0.125},
        "publish": {"model": "model-b", "route": "api", "cost_usd": 0.375},
    })
    _record_run(server, "monthly", "run-bad", "failed", {"prepare": "done", "publish": "failed"}, {
        "publish": {"model": "model-b", "route": "api", "cost_usd": 0.25},
    })

    result = server.post("/api/status/rebuild")
    assert result["written"] == ["status/monthly.md"]
    note = server.get("/api/status/monthly")["markdown"]
    assert "Monthly close" in note
    assert "run-ok" in note and "run-bad" in note
    assert "publish" in note and "failed" in note
    assert "2 runs" in note and "1 successful" in note and "50%" in note
    assert "model-a" in note and "model-b" in note
    assert "local" in note and "api" in note
    assert "0.75" in note

    repo = git.Repo(server.home + "/vault")
    commit = list(repo.iter_commits(paths="status/monthly.md", max_count=1))[0].hexsha
    assert server.post("/api/status/rebuild")["written"] == []
    assert list(repo.iter_commits(paths="status/monthly.md", max_count=1))[0].hexsha == commit
    assert repo.head.commit.message.startswith("[glacier-status]")


def test_render_uses_exact_usage_values_and_step_names(server):
    server.put("/api/environments/monthly", {
        "id": "monthly", "name": "Monthly close", "nodes": [
            {"id": "publish", "type": "command", "config": {}}
        ], "edges": []
    })
    _record_run(server, "monthly", "run-precise", "failed", {"publish": "failed"}, {
        "publish": {"model": "model-z", "route": "local-route", "cost_usd": 0.123456789},
    })
    note = server.get("/api/status/monthly")["markdown"]
    assert "publish" in note
    assert str(Decimal("0.123456789")) in note
    assert "local-route" in note and "model-z" in note


def test_status_note_lists_only_latest_ten_runs_and_cost_for_those_runs(server):
    server.put("/api/environments/monthly", {"id": "monthly", "name": "Monthly close", "nodes": [], "edges": []})
    for index in range(11):
        _record_run(server, "monthly", f"run-{index:02d}", "done", {}, {
            # Values use distinct magnitudes so the total and displayed run window are checkable.
            "usage": {"model": "model", "route": "route", "cost_usd": index + 0.1},
        })
    note = server.get("/api/status/monthly")["markdown"]
    assert "run-00" not in note
    assert all(f"run-{index:02d}" in note for index in range(1, 11))
    assert "$56.1" in note  # Exact total across all recorded run usage.
    assert "$10.1" in note  # Exact cost for the newest run.
