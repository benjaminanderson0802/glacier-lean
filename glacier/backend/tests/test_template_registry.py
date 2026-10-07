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
        {"id": "paid", "type": "decide", "config": {"engine": "gateway", "gateway": {"routes": [{"name": "hosted", "paid": True}]}}, "position": {"x": 520, "y": 0}},
    ]
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"])
    for item in ("acceptance", "curl", "wget", "nc", "ssh", "scp", "rm -rf", "sudo", "{secret:}", "paid"):
        assert item in findings


def test_all_requested_risky_command_forms_are_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    commands = [
        "rm -fr /tmp/x", "rm -r -f /tmp/x", "python -c 'print(1)'",
        "perl -e 'print 1'", "node -e 'console.log(1)'",
        "Invoke-WebRequest https://example.invalid", "iwr https://example.invalid",
        "certutil -urlcache https://example.invalid",
    ]
    flow["nodes"][0]["config"]["cmd"] = "; ".join(commands)
    flow["acceptance"] = [{"kind": "command", "cmd": "rm -r -f /tmp/also"}]
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"]).casefold()
    for pattern in ("rm -fr", "rm -r -f", "python -c", "perl -e", "node -e", "invoke-webrequest", "iwr", "certutil"):
        assert pattern in findings


def test_destructive_command_heuristic_flags_posix_and_powershell_forms(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    commands = [
        "rm -rf /tmp/x", "rm -rfv /tmp/x", "rm -fr /tmp/x", "rm -r -f /tmp/x",
        "rm -f -r /tmp/x", "rm --recursive /tmp/x", "Remove-Item C:\\temp\\x -Recurse",
        "del /s C:\\temp\\x", "rd /s C:\\temp\\x", "find . -delete",
    ]
    flow = _clean_flow()
    flow["nodes"][0]["config"]["cmd"] = "; ".join(commands)
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"]).casefold()
    for command in ("rm", "remove-item", "del /s", "rd /s", "find", "-delete"):
        assert command in findings


def test_recursive_rm_long_options_and_pwsh_are_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["nodes"][0]["config"]["cmd"] = "rm -f --recursive x; rm --force --recursive x; pwsh.exe -Command Get-Item"
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"]).casefold()
    assert findings.count("recursive rm") >= 2
    assert "pwsh" in findings


def test_gateway_engine_is_not_paid_by_itself_and_missing_paid_flag_is_paid(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["nodes"][0]["config"]["gateway"] = {"routes": [{"name": "local", "paid": False}]}
    flow["nodes"][0]["config"]["engine"] = "gateway"
    assert template_registry.review_import(_portable(flow))["accepted"] is True

    flow["nodes"][0]["config"]["gateway"] = {"routes": [{"name": "unspecified"}]}
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    assert any("paid" in finding.lower() for finding in result["review"])


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
    expected_commands = ["printf hello", "test -n '{prev_output}'"]
    assert proposal["commands_for_review"] == expected_commands
    saved = json.loads((tmp_path / "templates" / "pending" / f"{proposal['id']}.json").read_text())
    assert saved["commands_for_review"] == expected_commands
    codex = next(node for node in saved["template"]["nodes"] if node["type"] == "codex")
    assert codex["config"]["sandbox"] == "read-only"
    approved = client.post(f"/api/templates/import/{proposal['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert any(item["id"] == "community-safe" for item in client.get("/api/templates").json())


def test_scans_commands_in_acceptance_and_nested_plugin_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["acceptance"] = [{"kind": "command", "cmd": "curl https://example.invalid"}]
    flow["nodes"][0]["type"] = "codex"
    flow["nodes"][0]["config"] = {"options": {"command": "powershell -EncodedCommand abc"}}
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    findings = "\n".join(result["review"])
    assert "acceptance" in findings.lower()
    assert "curl" in findings.lower()
    assert "powershell" in findings.lower() or "encodedcommand" in findings.lower()


def test_all_codex_nodes_are_forced_read_only_and_ids_are_namespaced(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["id"] = "tpl-daily-report"
    for node in flow["nodes"]:
        if node["type"] == "codex":
            node["config"]["sandbox"] = "workspace-write"
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is True
    assert result["template_id"].startswith("community-")
    saved = json.loads((tmp_path / "templates" / "pending" / f"{result['id']}.json").read_text())
    assert saved["template"]["id"].startswith("community-")
    codex = next(node for node in saved["template"]["nodes"] if node["type"] == "codex")
    assert codex["config"]["sandbox"] == "read-only"


def test_codex_without_config_is_saved_read_only(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["nodes"][1].pop("config")
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is True
    saved = json.loads((tmp_path / "templates" / "pending" / f"{result['id']}.json").read_text())
    codex = next(node for node in saved["template"]["nodes"] if node["type"] == "codex")
    assert codex["config"] == {"sandbox": "read-only"}


def test_gateway_routes_are_reviewed_for_paid_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["nodes"][0]["config"]["gateway"] = {"routes": [{"name": "hosted", "paid": True}]}
    result = template_registry.review_import(_portable(flow))
    assert result["accepted"] is False
    assert any("paid" in finding.lower() for finding in result["review"])


def test_paid_route_scan_only_treats_entries_in_routes_lists_as_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = _clean_flow()
    flow["nodes"][0]["config"]["plugin"] = {"name": "calendar", "paid": True}
    clean = template_registry.review_import(_portable(flow))
    assert clean["accepted"] is True

    flow["nodes"][0]["config"]["plugin"]["routes"] = [{"name": "hosted", "paid": True}]
    paid = template_registry.review_import(_portable(flow))
    assert paid["accepted"] is False
    assert any("paid" in finding.lower() for finding in paid["review"])


def test_approve_rejects_malformed_proposal_ids_before_path_lookup(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    for proposal_id in ("../outside", "a" * 31, "g" * 32):
        try:
            template_registry.approve_import(proposal_id)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("malformed proposal id should be reported as not found")


def test_approve_route_returns_404_for_malformed_proposal_id():
    app = FastAPI()
    app.include_router(template_routes.router)
    response = TestClient(app).post("/api/templates/import/../outside/approve")
    assert response.status_code == 404
