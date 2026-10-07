import os

import pytest

import system_check


@pytest.mark.parametrize(
    "machine, expected",
    [
        ({"memory_gb": 8, "cpu_cores": 8, "ollama_models": ["qwen3:8b", "qwen3:0.6b"]}, {"mode": "low", "local_model": "qwen3:0.6b", "max_parallel_runs": 1}),
        ({"memory_gb": 16, "cpu_cores": 4, "ollama_models": ["qwen3:0.6b", "qwen3:8b"]}, {"mode": "low", "local_model": "qwen3:0.6b", "max_parallel_runs": 1}),
        ({"memory_gb": 16, "cpu_cores": 8, "ollama_models": ["qwen3:0.6b", "qwen3:8b"]}, {"mode": "standard", "local_model": "qwen3:0.6b", "max_parallel_runs": 4}),
        ({"memory_gb": 16, "cpu_cores": 8, "ollama_models": []}, {"mode": "standard", "local_model": "qwen3:0.6b", "max_parallel_runs": 4}),
    ],
)
def test_recommendation_table(machine, expected):
    assert system_check.recommend(machine) == expected


def test_check_reports_missing_tools_and_friendly_message(monkeypatch):
    monkeypatch.setattr(system_check.shutil, "which", lambda _name: None)
    result = system_check.check_system()
    assert set(result["tools"]) == {"codex", "ollama", "git", "python", "node"}
    assert all(tool == {"found": False, "version": ""} for tool in result["tools"].values())
    assert result["ollama_models"] == []
    assert any("Ollama" in message or "Codex" in message for message in result["messages"])


def test_check_reads_models_from_fake_ollama_on_path(tmp_path, monkeypatch):
    script = tmp_path / "ollama"
    script.write_text("#!/bin/sh\nprintf 'NAME\tID\nqwen3:0.6b\t1\nllama3.2:1b\t2\n'\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(system_check.shutil, "which", lambda name: str(script) if name == "ollama" else None)
    monkeypatch.setattr(system_check, "_machine_stats", lambda: (4, 8.0, 10.0))
    result = system_check.check_system()
    assert result["tools"]["ollama"]["found"] is True
    assert result["ollama_models"] == ["qwen3:0.6b", "llama3.2:1b"]
    assert result["recommended"]["local_model"] == "qwen3:0.6b"


def test_settings_environment_overrides_recommendation(monkeypatch):
    monkeypatch.setattr(system_check, "_machine_stats", lambda: (8, 16.0, 10.0))
    monkeypatch.setattr(system_check, "_ollama_models", lambda: ["qwen3:0.6b"])
    monkeypatch.setenv("GLACIER_LOCAL_MODEL", "custom:1b")
    monkeypatch.setenv("GLACIER_MAX_PARALLEL_RUNS", "3")
    assert system_check.effective_settings() == {
        "mode": "standard", "local_model": "custom:1b", "max_parallel_runs": 3
    }


def test_system_endpoints(server):
    assert "recommended" in server.get("/api/system/check")
    assert server.get("/api/system/settings")["max_parallel_runs"] >= 1
