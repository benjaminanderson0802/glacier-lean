"""Acceptance checks for template provenance and community review."""

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import template_registry
from routes import templates as template_routes


ROOT = Path(__file__).resolve().parents[3]


def _portable(flow):
    return json.dumps({"glacier_flow": 1, "flow": flow})


def _clean_flow():
    return {
        "id": "community-safe", "name": "Safe community flow",
        "goal": "Print a welcome message",
        "acceptance": [{"kind": "command", "cmd": "test -n '{prev_output}'"}],
        "nodes": [
            {"id": "hello", "type": "command", "config": {"cmd": "printf hello"}, "position": {"x": 0, "y": 0}},
            {"id": "summarize", "type": "codex", "config": {"prompt": "Summarize"}, "position": {"x": 260, "y": 0}},
        ],
        "edges": [{"id": "e1", "source": "hello", "target": "summarize", "label": ""}],
    }


def test_manifest_hashes_match_all_bundled_templates():
    manifest = json.loads((ROOT / "templates" / "MANIFEST.json").read_text())
    entries = manifest["templates"]
    files = {path.name for path in (ROOT / "templates").glob("*.json") if path.name != "MANIFEST.json"}
    assert {entry["file"] for entry in entries} == files
    for entry in entries:
        data = (ROOT / "templates" / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert entry["license"] == "Apache-2.0"
        assert entry["reviewed_by"] and entry["reviewed_on"]


def test_tampered_template_is_marked_and_cannot_be_installed(tmp_path, monkeypatch):
    entry = {"file": "one.json", "id": "one", "name": "One", "description": "One", "author": "Glacier", "license": "Apache-2.0", "sha256": "0" * 64, "reviewed_by": "owner", "reviewed_on": "2026-10-07"}
    (tmp_path / "one.json").write_text(json.dumps(_clean_flow()))
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"templates": [entry]}))
    monkeypatch.setattr(template_registry, "BUNDLED_DIR", tmp_path)
    result = template_registry.list_templates()
    assert result[0]["review_status"] == "changed since review"
    assert result[0]["installable"] is False


def test_risky_template_is_rejected_with_each_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["acceptance"] = []
    flow["edges"] = []
    flow["nodes"] = [
        {"id": "danger", "type": "command", "config": {"cmd": "curl x; wget y; nc x; ssh x; scp x; rm -rf /tmp/x; sudo id; printf '{secret:token}'"}, "position": {"x": 0, "y": 0}},
        {"id": "ai", "type": "codex", "config": {"prompt": "inspect"}, "position": {"x": 260, "y": 0}},
        {"id": "paid", "type": "decide", "config": {"engine": "gateway", "routes": "paid"}, "position": {"x": 520, "y": 0}},
    ]
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"])
    for item in ("acceptance", "curl", "wget", "nc", "ssh", "scp", "rm -rf", "sudo", "{secret:}", "paid"):
        assert item in findings


def test_clean_template_is_pending_then_approved_and_listed(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    app = FastAPI()
    app.include_router(template_routes.router)
    client = TestClient(app)

    response = client.post("/api/templates/import", json={"file": _portable(_clean_flow())})
    assert response.status_code == 200
    proposal = response.json()
    assert proposal["accepted"] is True
    assert proposal["status"] == "pending"
    saved = json.loads((tmp_path / "templates" / "pending" / f"{proposal['id']}.json").read_text())
    codex = next(node for node in saved["template"]["nodes"] if node["type"] == "codex")
    assert codex["config"]["sandbox"] == "read-only"
    approved = client.post(f"/api/templates/import/{proposal['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert any(item["id"] == "community-safe" for item in client.get("/api/templates").json())
