"""Memory links follow the same local, case-insensitive rules for note and graph views."""

import os


def test_memory_note_links_resolve_exactly_like_graph_edges(server):
    notes = {
        "source/index.md": """# Source
[[bare]] [[folder/Path Note]] [[renamed|Shown]] [[topic#Heading]]
[[topic#^block]] [[with extension.md]] ![[embedded]] ![[images/diagram.png]]
[Markdown](folder/Markdown%20Note.md) [[not-written]]
`[[inline-ghost]]`
```md
[[fenced-ghost]]
```
[external](https://example.com/out.md)
""",
        "source/bare.md": "# Local bare",
        "elsewhere/bare.md": "# Other bare",
        "folder/Path Note.md": "# Path Note",
        "source/renamed.md": "# Renamed",
        "source/topic.md": "# Topic",
        "source/with extension.md": "# Extension",
        "source/embedded.md": "# Embedded",
        "folder/Markdown Note.md": "# Markdown",
        "source/incoming.md": "[[SOURCE/INDEX#Heading]]",
    }
    for path, body in notes.items():
        server.put("/api/memory/note", {"path": path, "body": body, "author": "owner"})
    image = os.path.join(server.home, "vault", "images", "diagram.png")
    os.makedirs(os.path.dirname(image), exist_ok=True)
    with open(image, "wb") as attachment:
        attachment.write(b"image fixture")

    expected_out = {
        "source/index": {
            "source/bare", "folder/Path Note", "source/renamed", "source/topic",
            "source/with extension", "source/embedded", "folder/Markdown Note", "not-written",
        },
        "source/bare": set(), "elsewhere/bare": set(), "folder/Path Note": set(),
        "source/renamed": set(), "source/topic": set(), "source/with extension": set(),
        "source/embedded": set(), "folder/Markdown Note": set(), "source/incoming": {"source/index"},
    }
    expected_in = {
        "source/index": {"source/incoming"},
        "source/bare": {"source/index"}, "elsewhere/bare": set(),
        "folder/Path Note": {"source/index"}, "source/renamed": {"source/index"},
        "source/topic": {"source/index"}, "source/with extension": {"source/index"},
        "source/embedded": {"source/index"}, "folder/Markdown Note": {"source/index"},
        "source/incoming": set(),
    }
    graph = server.get("/api/memory/graph")
    graph_out = {}
    for edge in graph["edges"]:
        if edge["kind"] == "link":
            graph_out.setdefault(edge["source"], set()).add(edge["target"])

    for path in notes:
        note = server.get("/api/memory/note", params={"path": path})
        note_id = path.removesuffix(".md")
        assert set(note["links_out"]) == expected_out[note_id]
        assert set(note["links_in"]) == expected_in[note_id]
        assert graph_out.get(note_id, set()) == expected_out[note_id]
    assert {n["id"]: n["kind"] for n in graph["nodes"]}["not-written"] == "unresolved"
    index = server.get("/api/memory/note", params={"path": "source/index.md"})
    assert {item["target"] for item in index["links_out_status"] if item["status"] == "unresolved"} == {"not-written"}


def test_short_bare_name_prefers_same_folder_then_shortest_path(server):
    for path in ("area/current.md", "area/deep/target.md", "area/target.md", "target.md", "other/target.md"):
        body = "[[target]]" if path == "area/current.md" else "# Target"
        server.put("/api/memory/note", {"path": path, "body": body, "author": "owner"})
    note = server.get("/api/memory/note", params={"path": "area/current.md"})
    assert note["links_out"] == ["area/target"]
    assert server.get("/api/memory/note", params={"path": "area/target.md"})["links_in"] == ["area/current"]


def test_short_bare_name_uses_shortest_path_outside_current_folder(server):
    for path in ("origin/current.md", "long/nested/target.md", "near/target.md", "other/target.md"):
        body = "[[target]]" if path == "origin/current.md" else "# Target"
        server.put("/api/memory/note", {"path": path, "body": body, "author": "owner"})
    note = server.get("/api/memory/note", params={"path": "origin/current.md"})
    assert note["links_out"] == ["near/target"]


def test_relative_markdown_links_resolve_from_the_notes_folder():
    from memory_links import LinkResolver
    resolver = LinkResolver(["projects/a/plan.md", "projects/b/notes.md", "top.md"])
    assert resolver.resolve("../b/notes.md", "projects/a/plan.md") == ("projects/b/notes", "resolved")
    assert resolver.resolve("./plan.md", "projects/a/other.md") == ("projects/a/plan", "resolved")
    assert resolver.resolve("../../top.md", "projects/a/plan.md") == ("top", "resolved")
    assert resolver.resolve("../../../outside.md", "projects/a/plan.md")[1] == "unresolved"


def test_link_parser_handles_obsidian_and_markdown_edge_cases():
    from memory_links import parse_links

    body = (
        "`[[inline-ghost]]` and ``[[also-ghost]]``\n"
        "```md\n[[fenced-ghost]]\n```\n"
        "[[target#Heading|Shown]] ![[image.png#crop]] "
        "[relative](../folder/note.md) [external](https://example.com/note.md)"
    )
    assert parse_links(body) == [
        ("target", False), ("image.png", True), ("../folder/note", False),
    ]
