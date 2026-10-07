"""Acceptance checks for the offline guided first-run proposal and apply flow."""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import os

import system_check
import starter
from routes import starter as starter_routes


def _client(monkeypatch, tmp_path, machine):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.delenv("GLACIER_LOCAL_MODEL", raising=False)
    monkeypatch.delenv("GLACIER_MAX_PARALLEL_RUNS", raising=False)
    monkeypatch.setattr(system_check, "check_system", lambda: machine)
    import vault
    vault.init(str(tmp_path / "vault"))
    app = FastAPI()
    app.include_router(starter_routes.router)
    return TestClient(app)


def _machine(memory=8, models=None, tools=None):
    return {
        "cpu_cores": 8, "memory_gb": memory, "disk_free_gb": 20,
        "ollama_models": models or [],
        "tools": tools or {name: {"found": False, "version": ""}
                            for name in ("codex", "ollama", "git", "python", "node")},
        "recommended": system_check.recommend({"cpu_cores": 8, "memory_gb": memory, "ollama_models": models or []}),
    }


def test_low_memory_proposal_uses_light_mode_and_small_model(monkeypatch, tmp_path):
    response = _client(monkeypatch, tmp_path, _machine(memory=8)).get("/api/starter")
    assert response.status_code == 200
    proposal = response.json()
    assert proposal["mode"] == "low"
    assert proposal["local_model"] == "qwen3:0.6b"
    assert "8 GB" in proposal["reason"]


def test_no_ollama_suggests_no_local_model_template(monkeypatch, tmp_path):
    proposal = _client(monkeypatch, tmp_path, _machine()).get("/api/starter").json()
    for suggestion in proposal["suggested_automations"]:
        assert not suggestion["requires_local_model"]


def test_missing_coding_agent_has_license_and_official_link(monkeypatch, tmp_path):
    machine = _machine()
    machine["tools"]["ollama"] = {"found": True, "version": "ollama 1.0"}
    monkeypatch.setattr(starter, "_agent_discovery", lambda: [
        {"id": key, "name": name, "found": False, "version": "", "usable_as_step": False}
        for key, name in (("codex", "Codex"), ("opencode", "OpenCode"), ("gemini", "Gemini CLI"), ("claude", "Claude Code"))
    ])
    proposal = _client(monkeypatch, tmp_path, machine).get("/api/starter").json()
    missing = {item["name"]: item for item in proposal["missing_but_useful"]}
    assert "OpenCode" in missing
    assert missing["OpenCode"]["license"] == "MIT"
    assert missing["OpenCode"]["download_page"].startswith("https://opencode.ai/")


def test_apply_creates_only_chosen_flows_once_and_saves_settings(server, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", server.home)
    template_id = "tpl-inbox-triage"
    first = server.post("/api/starter/apply", {"template_ids": [template_id], "mode": "low"})
    result = first
    assert len(result["created"]) == 1
    assert result["created"][0]["template_id"] == template_id
    second = server.post("/api/starter/apply", {"template_ids": [template_id], "mode": "low"})
    assert second["created"] == []
    assert len(list((Path(server.home) / "vault" / "environments").glob("*.json"))) == 1
    settings = json.loads((Path(server.home) / "settings.json").read_text())
    assert settings["mode"] == "low"
    assert settings["local_model"] == "qwen3:0.6b"
    assert server.get("/api/system/settings")["local_model"] == "qwen3:0.6b"


def test_unknown_template_id_returns_plain_400(server):
    import httpx
    response = httpx.post(server.url + "/api/starter/apply", json={"template_ids": ["not-a-template"], "mode": "low"})
    assert response.status_code == 400
    assert response.json()["detail"] == "We could not find the selected starter automation."
