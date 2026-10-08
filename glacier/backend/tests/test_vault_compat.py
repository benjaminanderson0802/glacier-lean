import os
import sys


BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def _write_note_file(vault_path, name, text):
    if os.name == "nt" and (any(ord(char) < 32 for char in name) or ":" in os.path.basename(name)):
        # Win32 rejects control characters even through an extended path, and a ':' makes NTFS write
        # a hidden alternate stream of a different file instead, so these names cannot exist on Windows.
        return False
    path = os.path.join(vault_path, name)
    stem = os.path.basename(name).split(".", 1)[0].upper()
    reserved = stem in {"CON", "PRN", "AUX", "NUL"} or any(
        stem == f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    invalid = reserved or any(ord(char) < 32 or char in ':*?"<>|' for char in name)
    if os.name == "nt" and invalid:
        # The extended path prefix lets the test seed names Win32 normally
        # rejects so the compatibility checker can report them.
        path = "\\\\?\\" + os.path.abspath(path)
    with open(path, "w", encoding="utf-8") as note:
        note.write(text)
    return True


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
    bad_name = "bad: name.md"
    bad_name_seeded = _write_note_file(vault_path, bad_name, "---\ntitle: Bad name\n---\n# Bad name\n")
    with open(os.path.join(vault_path, "bad-yaml.md"), "w", encoding="utf-8") as note:
        note.write('---\ntitle: [unterminated\n---\n# Bad YAML\n')

    result = server.get("/api/memory/compat")
    problems = result["problems"]

    assert result["ok"] is False
    expected = {
        ("broken.md", "unresolved_link"),
        ("broken.md", "ambiguous_link"),
        ("bad-yaml.md", "invalid_front_matter"),
    }
    if bad_name_seeded:
        expected.add((bad_name, "invalid_filename"))
    assert len(problems) == len(expected)  # 4 on Linux and macOS; Windows cannot create the ':' file
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
        if name == "a\\b.md" and os.name == "nt":
            # On Windows this is a nested, valid path rather than one filename.
            os.makedirs(os.path.join(vault_path, "a"), exist_ok=True)
            name = os.path.join("a", "b.md")
        _write_note_file(vault_path, name, "# Name\n")

    result = server.get("/api/memory/compat")
    problems = result["problems"]

    expected = {
        ("nul.md", "invalid_filename"),
        ("hash#name.md", "link_unsafe_filename"),
        ("caret^name.md", "link_unsafe_filename"),
        ("bracket[name].md", "link_unsafe_filename"),
    }
    if os.name != "nt":
        expected.add(("control\x01.md", "invalid_filename"))
        expected.add(("a\\b.md", "invalid_filename"))
    assert {(p["path"], p["kind"]) for p in problems} == expected
    assert all(p["fix_hint"] for p in problems)


def test_backslash_link_paths_resolve_to_windows_vault_notes(server):
    vault_path = os.path.join(server.home, "vault")
    os.makedirs(os.path.join(vault_path, "a"), exist_ok=True)
    with open(os.path.join(vault_path, "a", "b.md"), "w", encoding="utf-8") as note:
        note.write("# B\n")
    with open(os.path.join(vault_path, "source.md"), "w", encoding="utf-8") as note:
        note.write("[[a\\b]]\n")

    result = server.get("/api/memory/compat")

    assert not any(problem["path"] == "source.md" and problem["kind"] == "unresolved_link" for problem in result["problems"])


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


def test_front_matter_helper_handles_crlf_empty_and_malformed_delimiters():
    from memory_meta import split_front_matter

    assert split_front_matter("---\r\n\r\n---\r\nBody") == ({}, "Body", None)
    metadata, body, error = split_front_matter("---\r\nname: [broken\r\nBody")
    assert metadata is None and body == "---\r\nname: [broken\r\nBody"
    assert error
