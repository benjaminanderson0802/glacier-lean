"""Keep the rebuildable vault index cheap to update without weakening Git history."""
import sqlite3

import pytest

import vault


@pytest.fixture
def temp_vault(tmp_path):
    old_vault, old_repo = vault.VAULT, vault._repo
    root = tmp_path / "vault"
    vault.init(str(root))
    try:
        yield root
    finally:
        if vault._repo is not old_repo:
            vault._repo.close()
        vault.VAULT, vault._repo = old_vault, old_repo


def test_vault_index_uses_wal_full_sync_and_keeps_search_current(temp_vault):
    root = temp_vault
    vault.write_note("one.md", "# Searchable token", author="owner")

    with sqlite3.connect(root / ".index.sqlite") as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    db = vault._db()
    try:
        assert db.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    finally:
        db.close()

    assert vault.search("Searchable") == ["one.md"]


def test_run_state_database_uses_wal_and_full_sync(tmp_path):
    import store

    old_db = store.DB
    try:
        store.init(str(tmp_path / "glacier.sqlite"))
        with store._conn() as db:
            assert db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert db.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    finally:
        store.DB = old_db


def test_repeated_vault_history_reads_reuse_git_log_and_refresh_after_save(temp_vault, monkeypatch):
    import git

    vault.write_note("one.md", "# First", author="owner")

    calls = 0
    original_execute = git.Git.execute

    def counted_execute(repo, command, *args, **kwargs):
        nonlocal calls
        if isinstance(command, (list, tuple)) and len(command) > 1 and command[1] == "log":
            calls += 1
        return original_execute(repo, command, *args, **kwargs)

    monkeypatch.setattr(git.Git, "execute", counted_execute)
    assert len(vault.note_history("one.md")) == 1
    assert len(vault.note_history("one.md")) == 1
    assert calls == 1

    vault.write_note("one.md", "# Second", author="owner")
    assert len(vault.note_history("one.md")) == 2
    assert calls == 2


def test_run_changes_reuse_git_log_until_a_matching_run_note_is_saved(temp_vault, monkeypatch):
    import git
    import rollback

    vault.write_note("owner.md", "# Owner note", author="owner")

    calls = 0
    original_execute = git.Git.execute

    def counted_execute(repo, command, *args, **kwargs):
        nonlocal calls
        if isinstance(command, (list, tuple)) and len(command) > 1 and command[1] == "log":
            calls += 1
        return original_execute(repo, command, *args, **kwargs)

    monkeypatch.setattr(git.Git, "execute", counted_execute)
    assert rollback.changes("run-123") == []
    assert rollback.changes("run-123") == []
    assert calls == 1

    vault.write_note("another.md", "# Unrelated", author="owner")
    assert rollback.changes("run-123") == []
    assert calls == 1

    vault.write_note("runs/run-123.md", "# Run note", agent="glacier-runner", run_id="run-123")
    changes = rollback.changes("run-123")
    assert len(changes) == 1 and changes[0]["path"] == "runs/run-123.md"
    assert rollback.changes("run-123") == changes
    assert calls == 2


def test_full_flow_restore_target_reuses_git_history_lookup(temp_vault, monkeypatch):
    import git
    import json
    import rollback

    vault.write_note("environments/flow.json", json.dumps({"id": "flow", "name": "Before"}),
                     agent="glacier-api")
    with vault._lock:
        first = vault._repo.head.commit.hexsha
    vault.write_note("environments/flow.json", json.dumps({"id": "flow", "name": "After"}),
                     agent="glacier-api")

    calls = 0
    original_execute = git.Git.execute

    def counted_execute(repo, command, *args, **kwargs):
        nonlocal calls
        if isinstance(command, (list, tuple)) and len(command) > 1 and command[1] == "rev-list":
            calls += 1
        return original_execute(repo, command, *args, **kwargs)

    monkeypatch.setattr(git.Git, "execute", counted_execute)
    path = "environments/flow.json"
    assert rollback._resolve_flow_version("flow", path, first) == {"id": "flow", "name": "Before"}
    assert rollback._resolve_flow_version("flow", path, first) == {"id": "flow", "name": "Before"}
    assert calls == 1
