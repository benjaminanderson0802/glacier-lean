"""npm .cmd shims are started through node directly so multi-line prompts survive on Windows."""
import os

import shell_commands

SHIM = ('@ECHO off\r\nGOTO start\r\n:find_dp0\r\nSET dp0=%~dp0\r\nEXIT /b\r\n:start\r\nSETLOCAL\r\nCALL :find_dp0\r\n'
        'IF EXIST "%dp0%\\node.exe" (\r\n  SET "_prog=%dp0%\\node.exe"\r\n) ELSE (\r\n  SET "_prog=node"\r\n)\r\n'
        'endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  "%dp0%\\node_modules\\@openai\\codex\\bin\\codex.js" %*\r\n')


def _shim(tmp_path, with_node=True):
    (tmp_path / "codex.cmd").write_text(SHIM, encoding="utf-8")
    script = tmp_path / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    if with_node:
        (tmp_path / "node.exe").write_text("", encoding="utf-8")
    return str(tmp_path / "codex.cmd"), str(script)


def test_shim_resolves_to_bundled_node_and_script(tmp_path):
    shim, script = _shim(tmp_path)
    assert shell_commands.npm_shim_command(shim) == [str(tmp_path / "node.exe"), script]


def test_shim_falls_back_to_node_on_path(tmp_path, monkeypatch):
    shim, script = _shim(tmp_path, with_node=False)
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: "/usr/bin/node" if name == "node" else None)
    assert shell_commands.npm_shim_command(shim) == ["/usr/bin/node", script]


def test_non_npm_or_missing_script_is_left_alone(tmp_path):
    other = tmp_path / "tool.cmd"
    other.write_text("@echo off\r\necho hi\r\n", encoding="utf-8")
    assert shell_commands.npm_shim_command(str(other)) is None
    shim, script = _shim(tmp_path)
    os.remove(script)
    assert shell_commands.npm_shim_command(shim) is None


def test_windows_invocation_uses_node_for_shims(tmp_path, monkeypatch):
    shim, script = _shim(tmp_path)
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    argv = shell_commands.executable_invocation(shim, "exec", "--", "line one\nline two")
    assert argv == [str(tmp_path / "node.exe"), script, "exec", "--", "line one\nline two"]
