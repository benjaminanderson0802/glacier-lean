"""Windows start-up safety: never start an extensionless npm script, never probe tools while the engine starts."""
import os
import sys

import shell_commands
import system_check


def _make(folder, name):
    path = folder / name
    path.write_text("@echo off\n", encoding="utf-8")
    return str(path)


def test_windows_which_skips_extensionless_npm_script(tmp_path, monkeypatch):
    _make(tmp_path, "codex")          # the Linux-style script npm also installs
    cmd = _make(tmp_path, "codex.cmd")
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: str(tmp_path / "codex"))
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")
    assert shell_commands.which("codex") == cmd


def test_windows_which_refuses_when_only_the_script_exists(tmp_path, monkeypatch):
    _make(tmp_path, "gemini")
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: str(tmp_path / "gemini"))
    monkeypatch.setenv("PATH", str(tmp_path))
    assert shell_commands.which("gemini") is None


def test_startup_settings_do_not_probe_tools(monkeypatch):
    system_check.clear_cache()
    probed = []
    monkeypatch.setattr(system_check, "_run", lambda command, *a, **k: probed.append(command) or "")
    monkeypatch.setattr(system_check, "_ollama_models", lambda: [])
    settings = system_check.effective_settings()
    assert settings["max_parallel_runs"] >= 1
    assert probed == []


def test_windows_which_trusts_a_not_found_answer(tmp_path, monkeypatch):
    """When the normal lookup finds nothing, do not go looking for other copies on PATH."""
    _make(tmp_path, "codex.cmd")
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: None)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert shell_commands.which("codex") is None


def test_windows_which_keeps_python_helpers(tmp_path, monkeypatch):
    helper = _make(tmp_path, "ollama.py")
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: helper)
    assert shell_commands.which("ollama") == helper
