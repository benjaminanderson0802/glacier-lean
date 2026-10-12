"""Ordinary unit regressions for links from a limited graph into older notes."""
import os

import vault
from routes import memory


def test_limited_graph_resolves_short_links_using_the_whole_vault(tmp_path):
    vault.init(str(tmp_path))
    project = tmp_path / "projects"
    project.mkdir()
    (project / "earlier.md").write_text("# Earlier", encoding="utf-8")
    (project / "latest.md").write_text("# Latest\n[[earlier|Read earlier]]", encoding="utf-8")
    os.utime(project / "earlier.md", (1_000_000_000, 1_000_000_000))
    os.utime(project / "latest.md", (2_000_000_000, 2_000_000_000))

    result = memory.graph(limit=1)

    assert {node["id"] for node in result["nodes"]} == {"projects/latest", "projects/earlier"}
    assert {tuple(edge.values()) for edge in result["edges"] if edge["kind"] == "link"} == {
        ("projects/latest", "projects/earlier", "link")
    }
    assert all(node["kind"] != "unresolved" for node in result["nodes"])


def test_limited_graph_does_not_follow_older_notes_outgoing_links(tmp_path):
    vault.init(str(tmp_path))
    for path, body, timestamp in [
        ("older.md", "# Older\n[[unrelated]]", 1_000_000_000),
        ("latest.md", "# Latest\n[[older]] [[missing]]", 2_000_000_000),
    ]:
        (tmp_path / path).write_text(body, encoding="utf-8")
        os.utime(tmp_path / path, (timestamp, timestamp))

    result = memory.graph(limit=1)

    assert {node["id"] for node in result["nodes"]} == {"latest", "older", "missing"}
    assert next(node for node in result["nodes"] if node["id"] == "missing")["kind"] == "unresolved"
    assert next(node for node in result["nodes"] if node["id"] == "older")["kind"] == "note"
