"""Acceptance tests for deterministic plain-language run explanations."""
import json
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import store
import importlib.util
from pathlib import Path

_ROUTE_PATH = Path(__file__).parents[1] / "routes" / "explain.py"
_SPEC = importlib.util.spec_from_file_location("explain_route", _ROUTE_PATH)
explain = importlib.util.module_from_spec(_SPEC)


@pytest.fixture
def explain_client(tmp_path, monkeypatch):
    _SPEC.loader.exec_module(explain)
    monkeypatch.setitem(sys.modules, "app", types.SimpleNamespace(NODE_CATALOG=[
        {"type": "command", "label": "Command"}, {"type": "note", "label": "Note"},
        {"type": "approval", "label": "Approval"},
    ]))
    db_path = tmp_path / "glacier.sqlite"
    store.init(str(db_path))
    import sqlite3
    with sqlite3.connect(db_path) as db:
        for table in ("glacier_runs", "glacier_nodes", "glacier_checks", "glacier_usage", "glacier_workspace"):
            db.execute(f"DELETE FROM {table}")
    app = FastAPI()
    app.include_router(explain.router)
    return TestClient(app)


def add_run(run_id, status, nodes, states, outputs=None, acceptance=None, waiting_on=None):
    graph = {"name": "Website check", "nodes": nodes, "edges": [],
             "acceptance": acceptance or []}
    with store._conn() as db:
        db.execute("INSERT INTO glacier_runs VALUES (?,?,?,?,?,?)",
                   (run_id, "website-check", status, "2026-10-07T12:00:00+00:00",
                    json.dumps(graph), waiting_on))
        db.executemany("INSERT INTO glacier_nodes VALUES (?,?,?,?)", [
            (run_id, node["id"], states[node["id"]], (outputs or {}).get(node["id"]))
            for node in nodes
        ])


def test_done_run_explains_steps_checks_and_verification(explain_client):
    add_run("done", "done", [
        {"id": "check-site", "type": "command", "config": {"cmd": "check website"}},
        {"id": "save", "type": "note", "config": {"path": "reports/site.md"}},
    ], {"check-site": "done", "save": "done"},
        {"check-site": "Found 2 changes", "save": "Saved a note"},
        acceptance=[{"kind": "command", "cmd": "check website", "required": True, "check": "website responds"}])
    store.record_check("done", 0, "command", True, "passed")
    with store._conn() as db:
        db.execute("UPDATE glacier_runs SET status='done' WHERE run_id='done'")
    assert store.checks_of("done") == [{"check": 0, "kind": "command", "passed": True, "evidence": "passed"}]

    response = explain_client.get("/api/runs/done/explain")
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["needs_you"] is None
    assert len(body["steps"]) == 2
    assert "2 changes" in body["summary"]
    assert "passed" in body["summary"]


def test_failed_missing_secret_gives_plain_advice_and_redacts_output(explain_client, monkeypatch):
    import secrets_store
    monkeypatch.setattr(secrets_store, "redact", lambda text: text.replace("secret-value", "[secret mail]"))
    add_run("failed", "failed", [
        {"id": "send", "type": "command", "config": {"cmd": "send report"}},
    ], {"send": "failed"}, {"send": "SMTP_PASSWORD is missing: secret-value"})

    body = explain_client.get("/api/runs/failed/explain").json()
    assert body["verified"] is False
    assert "Settings > Secrets" in body["steps"][0]["sentence"]
    assert "secret-value" not in json.dumps(body)


def test_waiting_approval_says_what_owner_must_decide(explain_client):
    add_run("waiting", "waiting", [
        {"id": "approve", "type": "approval", "config": {"prompt": "Send the weekly report?"}},
    ], {"approve": "waiting"}, {"approve": "waiting for approval"}, waiting_on="approve")

    body = explain_client.get("/api/runs/waiting/explain").json()
    assert "Send the weekly report?" in body["needs_you"]
    assert body["verified"] is None


def test_rejected_run_is_explained_as_owner_rejection(explain_client):
    add_run("rejected", "rejected", [
        {"id": "approve", "type": "approval", "config": {"prompt": "Publish the report?"}},
    ], {"approve": "done"}, {"approve": "rejected"})

    body = explain_client.get("/api/runs/rejected/explain").json()
    assert "rejected" in body["summary"].lower()
    assert body["verified"] is False


def test_unknown_run_is_404(explain_client):
    assert explain_client.get("/api/runs/missing/explain").status_code == 404


@pytest.mark.parametrize("status", ["done", "failed", "rejected", "waiting"])
def test_summary_has_at_most_three_sentences(explain_client, status):
    waiting_on = "approve" if status == "waiting" else None
    add_run(f"summary-{status}", status, [
        {"id": "approve", "type": "approval", "config": {"prompt": "Continue?"}},
    ], {"approve": "waiting" if status == "waiting" else "failed"},
        {"approve": "check failed"}, waiting_on=waiting_on)
    summary = explain_client.get(f"/api/runs/summary-{status}/explain").json()["summary"]
    assert summary.count(".") <= 3
