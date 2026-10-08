"""A vault reached through another spelling of its folder still saves and lists notes.

On Windows the same folder can be C:\\Users\\RUNNER~1\\... (8.3 short name) and
C:\\Users\\runneradmin\\...; note paths are resolved, so the vault root must be too.
A symlinked folder is the Linux equivalent of that second spelling.
"""
import os

import pytest

import vault


def test_vault_opened_through_an_alias_saves_and_lists_notes(tmp_path):
    real = tmp_path / "real-home"
    real.mkdir()
    alias = tmp_path / "alias-home"
    try:
        os.symlink(real, alias, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"this system refused to create a test symlink: {exc}")
    vault.init(str(alias / "vault"))
    vault.write_note("notes/decision.md", "# Decision\n\nKeep it lean.", agent="test")
    assert "notes/decision.md" in vault.list_notes()
    assert "Keep it lean." in vault.read_note("notes/decision.md")
    assert vault.VAULT == os.path.realpath(str(real / "vault"))
