import git
from pathlib import Path
import httpx
import pytest

import memory_hygiene
import vault


def _commit_seeded_notes(server):
    repo = git.Repo(server.home + "/vault")
    repo.index.add([str(path.relative_to(Path(server.home) / "vault")) for path in (Path(server.home) / "vault").rglob("*.md")])
    repo.index.commit("seed memory hygiene test notes")


def test_scan_proposes_duplicates_without_changing_notes(server):
    one = "---\ntitle: First\ncreated: 2026-10-01T00:00:00Z\n---\nSame useful memory.\n"
    two = "---\ntitle: Second\ncreated: 2026-10-02T00:00:00Z\n---\nSame useful memory.\n"
    root = Path(server.home) / "vault" / "notes"
    root.mkdir(parents=True)
    (root / "first.md").write_text(one)
    (root / "second.md").write_text(two)
    _commit_seeded_notes(server)
    before = git.Repo(server.home + "/vault").head.commit.hexsha
    # The hygiene scan can also run through its route and must be proposal-only.
    response = httpx.post(server.url + "/api/memory/hygiene/scan")
    assert response.status_code == 200
    proposals = response.json()
    duplicate = next(p for p in proposals if p["kind"] == "merge")
    assert set(duplicate["paths"]) == {"notes/first.md", "notes/second.md"}
    assert (root / "first.md").read_text() == one
    assert (root / "second.md").read_text() == two
    assert git.Repo(server.home + "/vault").head.commit.hexsha == before


def test_approve_merge_keeps_oldest_removes_duplicate_and_records_git_change(server):
    home = server.home
    first = "---\ntitle: First\ncreated: 2026-01-01T00:00:00Z\n---\nShared facts.\n"
    second = "---\ntitle: Second\ncreated: 2026-02-01T00:00:00Z\n---\nShared facts.\n"
    (Path(home) / "vault" / "notes").mkdir(parents=True)
    (Path(home) / "vault" / "notes" / "first.md").write_text(first)
    (Path(home) / "vault" / "notes" / "second.md").write_text(second)
    _commit_seeded_notes(server)
    response = httpx.post(server.url + "/api/memory/hygiene/scan")
    assert response.status_code == 200
    proposal = next(p for p in response.json() if p["kind"] == "merge")
    repo = git.Repo(home + "/vault")
    before = len(list(repo.iter_commits()))
    result = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": True})
    assert result.status_code == 200
    assert not (Path(home) / "vault" / "notes" / "second.md").exists()
    merged = (Path(home) / "vault" / "notes" / "first.md").read_text()
    assert "Shared facts." in merged
    assert "## Merged from notes/second.md" in merged
    assert len(list(repo.iter_commits())) == before + 1
    assert repo.head.commit.message.startswith("[glacier-hygiene]")


def test_rejected_proposal_is_remembered_and_linked_stale_run_is_excluded(server):
    root = Path(server.home) / "vault"
    (root / "runs").mkdir(parents=True)
    (root / "runs" / "old.md").write_text("---\ncreated: 2020-01-01T00:00:00Z\n---\nOld run.\n")
    (root / "notes").mkdir()
    (root / "notes" / "ref.md").write_text("Useful reference: [[runs/old]].\n")
    (root / "claims").mkdir()
    (root / "claims" / "reference.md").write_text("Claim evidence: [[runs/old]].\n")
    (root / "notes" / "a.md").write_text("Exact repeat\n")
    (root / "notes" / "b.md").write_text("Exact repeat\n")
    _commit_seeded_notes(server)
    response = httpx.post(server.url + "/api/memory/hygiene/scan")
    assert response.status_code == 200
    proposal = next(p for p in response.json() if p["kind"] == "merge")
    rejected = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": False})
    assert rejected.status_code == 200
    rescanned = httpx.post(server.url + "/api/memory/hygiene/scan").json()
    assert all(p["id"] != proposal["id"] for p in rescanned)
    assert all("runs/old.md" not in p["paths"] for p in rescanned)


def test_approve_archive_moves_stale_run_note_with_git_history(server):
    note = Path(server.home) / "vault" / "runs" / "old.md"
    note.parent.mkdir(parents=True)
    note.write_text("---\ncreated: 2020-01-01T00:00:00Z\n---\nOld run.\n")
    _commit_seeded_notes(server)
    response = httpx.post(server.url + "/api/memory/hygiene/scan")
    assert response.status_code == 200
    proposal = next(p for p in response.json() if p["kind"] == "archive")
    result = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": True})
    assert result.status_code == 200
    assert not note.exists()
    assert (note.parent.parent / "archive" / "runs" / "old.md").exists()


def test_get_only_reads_saved_proposals_and_claim_duplicates_are_excluded(server):
    root = Path(server.home) / "vault" / "claims"
    root.mkdir(parents=True)
    (root / "one.md").write_text("Same claim\n")
    (root / "two.md").write_text("Same claim\n")
    _commit_seeded_notes(server)
    first = httpx.get(server.url + "/api/memory/hygiene")
    assert first.status_code == 200
    assert first.json() == []
    saved = Path(server.home) / "hygiene.json"
    assert not saved.exists()
    scan = httpx.post(server.url + "/api/memory/hygiene/scan")
    assert scan.status_code == 200
    assert scan.json() == []
    assert saved.exists()


def test_merge_rewrites_links_and_keeps_raw_front_matter(server):
    root = Path(server.home) / "vault"
    (root / "notes").mkdir(parents=True)
    first = "---\ntitle: First\nauthor: owner\ncreated: 2026-01-01T00:00:00Z\n---\nShared facts.\n"
    second = "---\ntitle: Second\nauthor: worker:test\nrun_id: run-2\ncreated: 2026-02-01T00:00:00Z\n---\nShared facts.\n"
    (root / "notes" / "first.md").write_text(first)
    (root / "notes" / "second.md").write_text(second)
    (root / "notes" / "ref.md").write_text("See [[notes/second|the duplicate]].\n")
    _commit_seeded_notes(server)
    response = httpx.post(server.url + "/api/memory/hygiene/scan")
    proposal = next(p for p in response.json() if p["kind"] == "merge")
    result = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": True})
    assert result.status_code == 200
    keeper = (root / "notes" / "first.md").read_text()
    assert "author: owner" in keeper and "created: 2026-01-01T00:00:00Z" in keeper
    assert "## Merged from notes/second.md" in keeper
    assert "author: worker:test" in keeper and "run_id: run-2" in keeper
    assert "[[notes/first|the duplicate]]" in (root / "notes" / "ref.md").read_text()


def test_merge_link_rewrite_preserves_aliases_fragments_and_ignores_code():
    raw = (
        "[[notes/second#Heading|the duplicate]] `[[notes/second]]`\n"
        "```md\n[[notes/second]]\n```\n"
    )
    rewritten = memory_hygiene._rewrite_links(raw, ["notes/second.md"], "notes/first.md")
    assert rewritten == (
        "[[notes/first#Heading|the duplicate]] `[[notes/second]]`\n"
        "```md\n[[notes/second]]\n```\n"
    )


def test_merge_front_matter_parser_preserves_nested_custom_yaml():
    from memory_meta import split_front_matter

    raw = "---\r\ncustom:\r\n  nested: [one, two]\r\n---\r\nBody\r\n"
    metadata, body, error = split_front_matter(raw)
    assert metadata == {"custom": {"nested": ["one", "two"]}}
    assert body == "Body\r\n"
    assert error is None


def test_commit_failure_restores_changed_and_removed_files(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "keep.md").write_text("original\n")
    (root / "remove.md").write_text("to remove\n")
    vault.init(str(root))
    repo = git.Repo(str(root))
    repo.index.add(["keep.md", "remove.md"])
    repo.index.commit("seed")
    before = repo.head.commit.hexsha

    def fail_commit(*args, **kwargs):
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(type(repo.index), "commit", fail_commit)
    with pytest.raises(ValueError, match="could not be saved"):
        memory_hygiene._commit_changes({"keep.md": "changed\n"}, ["remove.md"])
    assert (root / "keep.md").read_text() == "original\n"
    assert (root / "remove.md").read_text() == "to remove\n"
    assert repo.head.commit.hexsha == before
