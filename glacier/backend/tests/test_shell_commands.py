import os

import pytest

import shell_commands


def test_windows_commands_use_git_bash_and_convert_drive_paths(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: r"C:\Program Files\Git\bin\bash.exe")

    argv, use_shell, warning = shell_commands.command_invocation(r"cat C:\Users\Ada\notes.txt")

    assert argv == [r"C:\Program Files\Git\bin\bash.exe", "-lc", "cat /c/Users/Ada/notes.txt"]
    assert use_shell is False
    assert warning == ""


def test_windows_commands_fail_clearly_when_git_bash_is_missing(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "nt")
    monkeypatch.setattr(shell_commands.shutil, "which", lambda name: None)
    monkeypatch.setattr(shell_commands.os.path, "isfile", lambda path: False)

    with pytest.raises(RuntimeError, match="Git Bash was not found"):
        shell_commands.command_invocation("echo hello")


def test_linux_commands_keep_the_platform_shell(monkeypatch):
    monkeypatch.setattr(shell_commands.os, "name", "posix")

    argv, use_shell, warning = shell_commands.command_invocation("echo hello")

    assert argv == "echo hello"
    assert use_shell is True
    assert warning == ""
