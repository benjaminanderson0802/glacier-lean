"""Windows refuses to replace a file another reader has open; vault saves wait briefly instead of failing."""
import os

import pytest

import vault


def test_replace_retries_while_windows_reports_access_denied(tmp_path, monkeypatch):
    source, destination = tmp_path / "new.md", tmp_path / "note.md"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")
    real_replace, calls = os.replace, []

    def busy_twice(a, b):
        calls.append(1)
        if len(calls) <= 2:
            raise PermissionError(5, "Access is denied")
        real_replace(a, b)

    monkeypatch.setattr(vault.os, "name", "nt")
    monkeypatch.setattr(vault.os, "replace", busy_twice)
    vault.replace_file(str(source), str(destination), delay=0)
    assert destination.read_text(encoding="utf-8") == "new" and len(calls) == 3


def test_replace_gives_up_after_the_retry_budget(tmp_path, monkeypatch):
    def always_busy(a, b):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(vault.os, "name", "nt")
    monkeypatch.setattr(vault.os, "replace", always_busy)
    with pytest.raises(PermissionError):
        vault.replace_file("a", "b", attempts=3, delay=0)


def test_replace_does_not_retry_on_other_systems(tmp_path, monkeypatch):
    calls = []

    def denied(a, b):
        calls.append(1)
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(vault.os, "name", "posix")
    monkeypatch.setattr(vault.os, "replace", denied)
    with pytest.raises(PermissionError):
        vault.replace_file("a", "b", delay=0)
    assert len(calls) == 1


def test_safe_path_refuses_git_internals_and_escapes(tmp_path):
    vault.init(str(tmp_path / "vault"))
    for bad in (".git/config", "notes/../.git/HEAD", "../outside.md", "a/.git/x"):
        with pytest.raises(ValueError):
            vault.safe_path(bad)
    assert vault.safe_path("notes/fine.md").endswith(os.path.join("notes", "fine.md"))
