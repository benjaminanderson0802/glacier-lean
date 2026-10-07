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
    system_check.clear_cache()
    monkeypatch.setattr(system_check.shutil, "which", lambda _name: None)
    result = system_check.check_system()
    assert set(result["tools"]) == {"codex", "ollama", "git", "python", "node"}
    assert all(tool == {"found": False, "version": ""} for tool in result["tools"].values())
    assert result["ollama_models"] == []
    assert any("Ollama" in message or "Codex" in message for message in result["messages"])


def test_check_reads_models_from_fake_ollama_on_path(tmp_path, monkeypatch):
    system_check.clear_cache()
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
    system_check.clear_cache()
    monkeypatch.setattr(system_check, "_machine_stats", lambda: (8, 16.0, 10.0))
    monkeypatch.setattr(system_check, "_ollama_models", lambda: ["qwen3:0.6b"])
    monkeypatch.setattr(system_check.shutil, "which", lambda _name: None)
    monkeypatch.setenv("GLACIER_LOCAL_MODEL", "custom:1b")
    monkeypatch.setenv("GLACIER_MAX_PARALLEL_RUNS", "3")
    assert system_check.effective_settings() == {
        "mode": "standard", "local_model": "custom:1b", "max_parallel_runs": 3
    }
    assert system_check.check_system()["recommended"] == {
        "mode": "standard", "local_model": "qwen3:0.6b", "max_parallel_runs": 4
    }


def test_system_endpoints(server):
    system_check.clear_cache()
    assert "recommended" in server.get("/api/system/check")
    assert server.get("/api/system/settings")["max_parallel_runs"] >= 1


def test_recommend_skips_embedding_models():
    settings = system_check.recommend({
        "memory_gb": 16,
        "cpu_cores": 8,
        "ollama_models": ["nomic-embed-text:latest", "all-minilm:33m", "qwen3:8b"],
    })
    assert settings["local_model"] == "qwen3:8b"


def test_unknown_memory_is_not_treated_as_low(monkeypatch):
    monkeypatch.setattr(system_check.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(system_check.os, "sysconf", lambda key: (_ for _ in ()).throw(ValueError("unknown")))
    monkeypatch.setattr(system_check.shutil, "disk_usage", lambda _path: type("Usage", (), {"free": 20 * 1024**3})())
    cores, memory, _disk = system_check._machine_stats()
    assert cores >= 1
    assert memory is None
    assert system_check.recommend({"cpu_cores": 8, "memory_gb": memory})["mode"] == "standard"


def test_tool_with_nonzero_version_exit_is_not_found(monkeypatch):
    system_check.clear_cache()
    monkeypatch.setattr(system_check.shutil, "which", lambda name: "/fake/python" if name == "python" else None)
    monkeypatch.setattr(system_check, "_run", lambda _command, **_kwargs: "" )
    result = system_check.check_system()
    assert result["tools"]["python"] == {"found": False, "version": ""}


def test_disk_space_uses_glacier_home(monkeypatch, tmp_path):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(system_check.shutil, "disk_usage", lambda path: type("Usage", (), {"free": (100 if str(path) == str(tmp_path) else 1) * 1024**3})())
    _cores, _memory, disk = system_check._machine_stats()
    assert disk == 100.0


def test_check_system_caches_result_for_60_seconds(monkeypatch):
    calls = []
    monkeypatch.setattr(system_check, "_machine_stats", lambda: (calls.append("stats") or (8, 16.0, 20.0)))
    monkeypatch.setattr(system_check, "_ollama_models", lambda: [])
    monkeypatch.setattr(system_check.shutil, "which", lambda _name: None)
    monkeypatch.setattr(system_check.time, "monotonic", lambda: 10.0)
    system_check.clear_cache()
    first = system_check.check_system()
    second = system_check.check_system()
    assert first == second
    assert calls == ["stats"]


def test_missing_memory_is_reported_as_unknown(monkeypatch):
    monkeypatch.setattr(system_check, "_machine_stats", lambda: (8, None, 20.0))
    monkeypatch.setattr(system_check, "_ollama_models", lambda: [])
    monkeypatch.setattr(system_check.shutil, "which", lambda _name: None)
    system_check.clear_cache()
    result = system_check.check_system()
    assert result["memory_gb"] is None
    assert any("memory is unknown" in message.lower() for message in result["messages"])
