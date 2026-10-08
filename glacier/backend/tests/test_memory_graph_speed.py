"""Memory map output and same-machine performance regression checks."""
import os
import statistics
import time

import memory_meta
import vault
from memory_links import LinkResolver, resolve_links
from routes import memory


def _seed_note(path, body, author="owner"):
    full = vault.safe_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="") as note:
        note.write(memory_meta.render(path, body, author, "", None)[1])


def _legacy_graph(limit=None):
    """Pre-optimization graph implementation, retained as a same-process baseline."""
    items = []
    for path in vault.list_notes(".md"):
        try:
            meta, _ = vault.read_note_metadata(path)
            items.append({"path": path, **{key: meta[key] for key in ("title", "author", "updated", "tags")}})
        except (OSError, ValueError):
            continue

    def mtime(item):
        try:
            return os.stat(vault.safe_path(item["path"])).st_mtime_ns
        except OSError:
            return 0

    items.sort(key=mtime, reverse=True)
    if limit is not None:
        items = items[:limit]
    paths = [item["path"].removesuffix(".md") for item in items]
    attachments = []
    for root, dirs, files in os.walk(vault.VAULT):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in files:
            if not name.lower().endswith(".md"):
                attachments.append(os.path.relpath(os.path.join(root, name), vault.VAULT).replace(os.sep, "/"))
    resolver = LinkResolver(paths, attachments)
    links = {}
    for item in items:
        source = item["path"].removesuffix(".md")
        try:
            _, body = vault.read_note_metadata(item["path"])
            links[source] = resolve_links(body, source, resolver)
        except (OSError, ValueError):
            links[source] = []

    nodes, edges = [], []
    known = set()
    for item in items:
        source = item["path"].removesuffix(".md")
        known.add(source)
        nodes.append({"id": source, "title": item["title"], "kind": "note", "author": item["author"]})
        edges.append({"source": source, "target": item["author"], "kind": "wrote"})
    for source, refs in links.items():
        for ref in refs:
            target = ref["target"]
            kind = ("unresolved" if ref["status"] == "unresolved" else
                    "run" if target.startswith("runs/") else
                    "flow" if target.startswith("environments/") or target.startswith("flows/") else
                    "claim" if target.startswith("claims/") else "note")
            if target not in known:
                nodes.append({"id": target, "title": os.path.basename(target), "kind": kind, "author": ""})
                known.add(target)
            edges.append({"source": source, "target": target, "kind": "link"})
    return {"nodes": nodes, "edges": edges}


def test_graph_output_matches_legacy_for_link_variants_and_folders(server):
    vault.init(os.path.join(server.home, "vault"))
    notes = {
        "projects/alpha/plan.md": "# Plan\n\n[[projects/beta/notes|Beta]] ![[diagram.png]] [[missing note]] [relative](../beta/notes.md) [[runs/r-123]]",
        "projects/beta/notes.md": "# Notes\n\n[[plan#Overview]] [[Alias Target|friendly name]]",
        "projects/alpha/alias-target.md": "# Alias Target\n\n[[plan#^block]]",
        "runs/r-123.md": "# Run\n\n[[environments/daily]]",
        "environments/daily.md": "# Daily\n\n[[claims/open-claim]]",
        "claims/open-claim.md": "# Claim\n",
        "top.md": "# Top\n\n```md\n[[ignored-code]]\n```\n",
    }
    for path, body in notes.items():
        _seed_note(path, body, "owner" if path == "top.md" else "worker:test")
    os.makedirs(os.path.join(vault.VAULT, "projects", "alpha"), exist_ok=True)
    with open(os.path.join(vault.VAULT, "projects", "alpha", "diagram.png"), "wb") as attachment:
        attachment.write(b"image")
    with vault._lock:
        vault._repo.index.add(list(notes) + ["projects/alpha/diagram.png"])
        vault._repo.index.commit("seed graph variants")

    expected = _legacy_graph()
    actual = memory.graph()
    assert actual == expected
    assert {edge["target"] for edge in actual["edges"] if edge["source"] == "projects/alpha/plan"} >= {
        "projects/beta/notes", "projects/beta/notes", "missing note", "runs/r-123"
    }
    assert "ignored-code" not in {node["id"] for node in actual["nodes"]}


def test_graph_is_at_least_twice_as_fast_as_same_machine_legacy_baseline(server):
    vault.init(os.path.join(server.home, "vault"))
    paths = []
    for index in range(2000):
        path = f"bench/note-{index:04}.md"
        target = f"bench/note-{(index + 1) % 2000:04}"
        _seed_note(path, f"# Note {index}\n\nLinks [[{target}]].")
        paths.append(path)
    with vault._lock:
        vault._repo.index.add(paths)
        vault._repo.index.commit("seed 2,000 graph speed notes")

    # Warm the filesystem and metadata cache for both implementations; compare medians
    # from the same process so machine speed does not affect the ratio.
    _legacy_graph()
    memory.graph()
    baseline, optimized = [], []
    for _ in range(5):
        started = time.perf_counter()
        _legacy_graph()
        baseline.append(time.perf_counter() - started)
        started = time.perf_counter()
        memory.graph()
        optimized.append(time.perf_counter() - started)
    baseline_seconds = statistics.median(baseline)
    optimized_seconds = statistics.median(optimized)
    assert optimized_seconds <= baseline_seconds / 2, (
        f"graph median {optimized_seconds:.4f}s; legacy median {baseline_seconds:.4f}s; "
        f"speedup {baseline_seconds / optimized_seconds:.2f}x"
    )
