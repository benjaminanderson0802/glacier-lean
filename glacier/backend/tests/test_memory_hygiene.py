import git
from pathlib import Path
import httpx


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
    response = httpx.get(server.url + "/api/memory/hygiene")
    assert response.status_code == 200
    proposals = response.json()
    duplicate = next(p for p in proposals if p["kind"] == "merge")
    assert set(duplicate["paths"]) == {"notes/first.md", "notes/second.md"}
    assert httpx.get(server.url + "/api/vault/note", params={"path": "notes/first.md"}).json()["body"] == one
    assert httpx.get(server.url + "/api/vault/note", params={"path": "notes/second.md"}).json()["body"] == two
    assert git.Repo(server.home + "/vault").head.commit.hexsha == before


def test_approve_merge_keeps_oldest_removes_duplicate_and_records_git_change(server):
    home = server.home
    first = "---\ntitle: First\ncreated: 2026-01-01T00:00:00Z\n---\nShared facts.\n"
    second = "---\ntitle: Second\ncreated: 2026-02-01T00:00:00Z\n---\nShared facts.\n"
    (Path(home) / "vault" / "notes").mkdir(parents=True)
    (Path(home) / "vault" / "notes" / "first.md").write_text(first)
    (Path(home) / "vault" / "notes" / "second.md").write_text(second)
    _commit_seeded_notes(server)
    response = httpx.get(server.url + "/api/memory/hygiene")
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
    (root / "notes" / "a.md").write_text("Exact repeat\n")
    (root / "notes" / "b.md").write_text("Exact repeat\n")
    _commit_seeded_notes(server)
    response = httpx.get(server.url + "/api/memory/hygiene")
    assert response.status_code == 200
    proposal = next(p for p in response.json() if p["kind"] == "merge")
    rejected = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": False})
    assert rejected.status_code == 200
    rescanned = httpx.get(server.url + "/api/memory/hygiene").json()
    assert all(p["id"] != proposal["id"] for p in rescanned)
    assert all("runs/old.md" not in p["paths"] for p in rescanned)


def test_approve_archive_moves_stale_run_note_with_git_history(server):
    note = Path(server.home) / "vault" / "runs" / "old.md"
    note.parent.mkdir(parents=True)
    note.write_text("---\ncreated: 2020-01-01T00:00:00Z\n---\nOld run.\n")
    _commit_seeded_notes(server)
    response = httpx.get(server.url + "/api/memory/hygiene")
    assert response.status_code == 200
    proposal = next(p for p in response.json() if p["kind"] == "archive")
    result = httpx.post(server.url + f"/api/memory/hygiene/{proposal['id']}", json={"approve": True})
    assert result.status_code == 200
    assert not note.exists()
    assert (note.parent.parent / "archive" / "runs" / "old.md").exists()
