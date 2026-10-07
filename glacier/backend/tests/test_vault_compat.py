import os
import sys


BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def test_notes_written_through_memory_api_are_compatible(server):
    server.put("/api/memory/note", {
        "path": "projects/alpha.md",
        "body": "# Alpha\n\nSee [[projects/beta|Beta]] and embed ![[images/map.png]].",
        "author": "owner",
    })
    server.put("/api/memory/note", {
        "path": "projects/beta.md", "body": "# Beta", "author": "owner",
    })
    os.makedirs(os.path.join(server.home, "vault", "images"), exist_ok=True)
    with open(os.path.join(server.home, "vault", "images", "map.png"), "wb") as image:
        image.write(b"image")

    result = server.get("/api/memory/compat")

    assert result == {"ok": True, "notes_checked": 2, "problems": []}


def test_compatibility_reports_each_seeded_problem_once_with_a_hint(server):
    vault_path = os.path.join(server.home, "vault")
    os.makedirs(os.path.join(vault_path, "one"), exist_ok=True)
    os.makedirs(os.path.join(vault_path, "two"), exist_ok=True)
    with open(os.path.join(vault_path, "one", "twin.md"), "w", encoding="utf-8") as note:
        note.write("---\ntitle: Twin\n---\n# One\n")
    with open(os.path.join(vault_path, "two", "twin.md"), "w", encoding="utf-8") as note:
        note.write("---\ntitle: Twin\n---\n# Two\n")
    with open(os.path.join(vault_path, "broken.md"), "w", encoding="utf-8") as note:
        note.write("---\ntitle: Broken\n---\n[[missing-note]]\n[[twin]]\n")
    with open(os.path.join(vault_path, "bad: name.md"), "w", encoding="utf-8") as note:
        note.write("---\ntitle: Bad name\n---\n# Bad name\n")
    with open(os.path.join(vault_path, "bad-yaml.md"), "w", encoding="utf-8") as note:
        note.write('---\ntitle: [unterminated\n---\n# Bad YAML\n')

    result = server.get("/api/memory/compat")
    problems = result["problems"]

    assert result["ok"] is False
    assert len(problems) == 4
    expected = {
        ("broken.md", "unresolved_link"),
        ("broken.md", "ambiguous_link"),
        ("bad: name.md", "invalid_filename"),
        ("bad-yaml.md", "invalid_front_matter"),
    }
    assert {(problem["path"], problem["kind"]) for problem in problems} == expected
    assert all(problem["detail"] and problem["fix_hint"] for problem in problems)
    assert len({(problem["path"], problem["kind"], problem["detail"]) for problem in problems}) == len(problems)


def test_missing_embedded_attachment_is_reported(server):
    server.put("/api/memory/note", {
        "path": "photo.md", "body": "# Photo\n\nSee ![[images/missing.png]].", "author": "owner",
    })

    result = server.get("/api/memory/compat")

    assert [p["kind"] for p in result["problems"]] == ["missing_attachment"]
    assert result["problems"][0]["fix_hint"]


def test_compatibility_checks_windows_names_and_warns_on_obsidian_link_characters(server):
    vault_path = os.path.join(server.home, "vault")
    for name in ("nul.md", "a\\b.md", "control\x01.md", "hash#name.md", "caret^name.md", "bracket[name].md"):
        with open(os.path.join(vault_path, name), "w", encoding="utf-8") as note:
            note.write("# Name\n")

    result = server.get("/api/memory/compat")
    problems = result["problems"]

    assert {(p["path"], p["kind"]) for p in problems} == {
        ("nul.md", "invalid_filename"),
        ("a\\b.md", "invalid_filename"),
        ("control\x01.md", "invalid_filename"),
        ("hash#name.md", "link_unsafe_filename"),
        ("caret^name.md", "link_unsafe_filename"),
        ("bracket[name].md", "link_unsafe_filename"),
    }
    assert all(p["fix_hint"] for p in problems)


def test_link_checks_ignore_inline_and_fenced_code_and_partial_paths_match_folder(server):
    vault_path = os.path.join(server.home, "vault")
    os.makedirs(os.path.join(vault_path, "b"), exist_ok=True)
    os.makedirs(os.path.join(vault_path, "other"), exist_ok=True)
    with open(os.path.join(vault_path, "b", "c.md"), "w", encoding="utf-8") as note:
        note.write("# C in b\n")
    with open(os.path.join(vault_path, "other", "c.md"), "w", encoding="utf-8") as note:
        note.write("# C elsewhere\n")
    with open(os.path.join(vault_path, "links.md"), "w", encoding="utf-8") as note:
        note.write("Inline `[[missing-inline]]` and fenced:\n\n```md\n[[missing-fenced]]\n```\n\nReal [[b/c]].\n")

    result = server.get("/api/memory/compat")

    assert result["problems"] == []


def test_partial_path_does_not_fall_back_to_ambiguous_basename(server):
    vault_path = os.path.join(server.home, "vault")
    os.makedirs(os.path.join(vault_path, "a"), exist_ok=True)
    os.makedirs(os.path.join(vault_path, "b"), exist_ok=True)
    with open(os.path.join(vault_path, "a", "c.md"), "w", encoding="utf-8") as note:
        note.write("# A\n")
    with open(os.path.join(vault_path, "b", "c.md"), "w", encoding="utf-8") as note:
        note.write("# B\n")
    with open(os.path.join(vault_path, "source.md"), "w", encoding="utf-8") as note:
        note.write("[[missing/c]]\n")

    result = server.get("/api/memory/compat")

    assert [(p["path"], p["kind"]) for p in result["problems"]] == [("source.md", "unresolved_link")]
