"""Unit coverage for rebuilding disposable indexes from the vault's plain files."""
import subprocess

import vault


def test_clone_recovers_keyword_search_and_links_without_changing_git(tmp_path):
    source, restored = tmp_path / "source", tmp_path / "restored"
    vault.init(str(source))
    vault._repo.index.add([str(source / ".gitignore")])
    vault.write_note("notes/choice.md", "# Choice\nLighthouse [[notes/research|Research]]", author="owner")
    subprocess.run(["git", "clone", "-q", str(source), str(restored)], check=True)
    head = subprocess.check_output(["git", "-C", str(restored), "rev-parse", "HEAD"])

    vault.init(str(restored))

    assert vault.search("lighthouse") == ["notes/choice.md"]
    assert vault.links("notes/choice.md") == ["notes/research"]
    assert subprocess.check_output(["git", "-C", str(restored), "rev-parse", "HEAD"]) == head
    assert not subprocess.check_output(["git", "-C", str(restored), "status", "--porcelain"])


def test_restart_refreshes_offline_edits_and_removals_preserving_events(tmp_path):
    vault.init(str(tmp_path))
    vault.write_note("edited.md", "Oldword [[gone]]", author="owner")
    vault.write_note("gone.md", "Removedword", author="owner")
    (tmp_path / "edited.md").write_text("# Updated\nNewword [[added]]", encoding="utf-8")
    (tmp_path / "gone.md").unlink()
    (tmp_path / "added.md").write_text("# Added\nFreshword", encoding="utf-8")

    vault.init(str(tmp_path))
    vault.init(str(tmp_path))

    assert vault.search("oldword removedword") == []
    assert vault.search("newword") == ["edited.md"]
    assert vault.search("freshword") == ["added.md"]
    assert vault.links("edited.md") == ["added"]
    with vault._db() as db:
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 2


def test_recovery_keeps_json_search_and_excludes_front_matter_and_git(tmp_path):
    vault.init(str(tmp_path))
    vault.write_note("environments/flow.json", '{"name":"Flowword"}', author="owner")
    (tmp_path / "note.md").write_text("---\nsecretlabel: Metaword\n---\nBodyword", encoding="utf-8")
    (tmp_path / ".git" / "private.md").write_text("Gitword", encoding="utf-8")

    vault.init(str(tmp_path))

    assert vault.search("flowword") == ["environments/flow.json"]
    assert vault.search("bodyword") == ["note.md"]
    assert vault.search("metaword gitword") == []
