"""Commit details load lazily through GitPython's shared cat-file pipe.

Reading them after releasing vault._lock let a concurrent reader interleave on
that pipe ("SHA b'tree' could not be resolved"), so history and undo must read
every commit attribute while the lock is held.
"""
import threading

import git
import pytest

import vault
from routes import memory


class _TrackingLock:
    def __init__(self):
        self._inner = threading.RLock()
        self.depth = 0

    def __enter__(self):
        self._inner.acquire()
        self.depth += 1
        return self

    def __exit__(self, *exc):
        self.depth -= 1
        self._inner.release()
        return False

    def acquire(self, *a, **k):
        ok = self._inner.acquire(*a, **k)
        if ok:
            self.depth += 1
        return ok

    def release(self):
        self.depth -= 1
        self._inner.release()


@pytest.fixture
def tracked(tmp_path, monkeypatch):
    vault.init(str(tmp_path / "vault"))
    vault.write_note("note.md", "# One", author="owner")
    vault.write_note("note.md", "# Two", author="owner")
    lock = _TrackingLock()
    monkeypatch.setattr(vault, "_lock", lock)
    unlocked = []
    original = git.Commit._set_cache_

    def checked(self, attr):
        if lock.depth == 0:
            unlocked.append(attr)
        return original(self, attr)

    monkeypatch.setattr(git.Commit, "_set_cache_", checked)
    return unlocked


def test_history_reads_commit_details_under_the_vault_lock(tracked):
    entries = memory.history("note.md")
    assert [e["author"] for e in entries] == ["owner", "owner"]
    assert tracked == []


def test_undo_reads_commit_parents_under_the_vault_lock(tracked):
    result = memory.undo(memory.Undo(path="note.md"))
    assert result["path"] == "note.md"
    assert tracked == []
