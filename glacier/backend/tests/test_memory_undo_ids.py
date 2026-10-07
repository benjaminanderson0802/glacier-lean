import pytest
from fastapi import HTTPException

import vault
from routes import memory


@pytest.fixture
def memory_vault(tmp_path):
    vault.init(str(tmp_path / "vault"))
    return vault


@pytest.mark.parametrize("commit", ["a", "abcdef", "not-hex7"])
def test_memory_undo_rejects_short_or_non_hex_commit_ids(memory_vault, commit):
    memory_vault.write_note("note.md", "# Saved", author="owner")

    with pytest.raises(HTTPException) as error:
        memory.undo(memory.Undo(path="note.md", commit=commit))

    assert error.value.status_code == 400
    assert error.value.detail == "Enter at least 7 letters or numbers from the saved version ID."


def test_memory_undo_rejects_ambiguous_prefix(memory_vault, monkeypatch):
    class Commit:
        def __init__(self, hexsha):
            self.hexsha = hexsha

    class Repository:
        def iter_commits(self, paths):
            return iter([Commit("1234567a" + "0" * 32), Commit("1234567b" + "0" * 32)])

    monkeypatch.setattr(memory.vault, "_repo", Repository())

    with pytest.raises(HTTPException) as error:
        memory.undo(memory.Undo(path="note.md", commit="1234567"))

    assert error.value.status_code == 400
    assert error.value.detail == "More than one saved version matches. Enter more of the version ID."


def test_memory_undo_restores_exact_full_commit_id(memory_vault):
    memory_vault.write_note("note.md", "# Before", author="owner")
    saved = memory_vault.write_note("note.md", "# After", author="owner")

    result = memory.undo(memory.Undo(path="note.md", commit=saved))

    assert result["path"] == "note.md"
    assert memory_vault.read_raw_note("note.md").endswith("# Before")
