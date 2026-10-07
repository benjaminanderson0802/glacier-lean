"""Glacier memory vault: markdown/JSON notes tracked in git + SQLite keyword search + event log.
Importable (call init(path) once) and runnable as an MCP server: `python vault.py` (uses GLACIER_VAULT, default ./vault).
Every write is: atomic file write -> git commit -> index update. No AI models."""
import os, re, json, sqlite3, tempfile, threading
import git
import memory_meta

VAULT: str = ""
_repo = None
_lock = threading.Lock()


def init(path: str) -> None:
    global VAULT, _repo
    VAULT = os.path.abspath(path)
    os.makedirs(VAULT, exist_ok=True)
    _repo = git.Repo.init(VAULT)
    with open(os.path.join(VAULT, ".gitignore"), "w") as f:
        f.write(".index.sqlite*\n")


def _db():
    c = sqlite3.connect(os.path.join(VAULT, ".index.sqlite"), timeout=30)
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, body)")
    c.execute("CREATE TABLE IF NOT EXISTS links(src TEXT, dst TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS events(ts DEFAULT CURRENT_TIMESTAMP, agent TEXT, kind TEXT, data TEXT)")
    return c


def safe_path(path: str) -> str:
    """Absolute path inside the vault; raises ValueError on escapes like ../"""
    full = os.path.realpath(os.path.join(VAULT, path))
    if not full.startswith(VAULT + os.sep) or "/.git/" in full + "/":
        raise ValueError(f"bad vault path: {path}")
    return full


def write_note(path: str, body: str, agent: str = "unknown", *, author: str | None = None, run_id: str = "") -> str:
    """Create or replace a note; returns the short commit sha. Legacy agent callers remain supported."""
    full = safe_path(path)
    with _lock:
        previous = None
        try:
            with open(full, encoding="utf-8") as f:
                previous = f.read()
        except FileNotFoundError:
            pass
        # Keep the historical `agent=` call shape, while run note steps carry an
        # explicit run identity in the service-owned author field.
        writer = author or (f"run:{run_id}" if run_id else agent)
        metadata_run_id = run_id
        # Legacy internal writers (not the HTTP screen) encode their domain fields in
        # front matter. Carry a claim's run id into the service field when available.
        if path.endswith(".md") and not metadata_run_id and author is None and agent != "unknown":
            incoming = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", body, re.S)
            if incoming:
                run_line = re.search(r"(?m)^run_id:\s*(.*)$", incoming.group(1))
                if run_line:
                    metadata_run_id = run_line.group(1).strip().strip('"')
        stored_body = memory_meta.render(path, body, writer, metadata_run_id, previous)[1] if path.endswith(".md") else body
        os.makedirs(os.path.dirname(full), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(full))
        os.write(fd, stored_body.encode()); os.close(fd); os.replace(tmp, full)
        _repo.index.add([os.path.relpath(full, VAULT)])
        sha = _repo.index.commit(f"[{agent}] write {path}").hexsha[:8]
        c = _db()
        c.execute("DELETE FROM fts WHERE path=?", (path,)); c.execute("INSERT INTO fts VALUES (?,?)", (path, stored_body))
        c.execute("DELETE FROM links WHERE src=?", (path,))
        for dst in re.findall(r"\[\[([^\]]+)\]\]", body):
            c.execute("INSERT INTO links VALUES (?,?)", (path, dst.split("|", 1)[0].strip().removesuffix(".md")))
        c.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)", (writer, "write_note", json.dumps({"path": path, "commit": sha})))
        c.commit(); c.close()
        # Keep the change notification on the existing event channel without changing run-step events.
        try:
            import store
            event = {"type": "memory", "path": path,
                     "change": "created" if previous is None else "updated",
                     "author": writer, "run_id": metadata_run_id}
            if writer.startswith("run:"):
                # Let the associated run-step completion event reach clients first.
                threading.Timer(0.1, store.broadcaster.publish, args=(event,)).start()
            else:
                store.broadcaster.publish(event)
        except (ImportError, AttributeError):
            pass
    return sha


def read_note(path: str) -> str:
    return memory_meta.legacy_read(read_raw_note(path))


def read_raw_note(path: str) -> str:
    """Read the stored note, including service and caller front matter."""
    with open(safe_path(path), encoding="utf-8") as f:
        return f.read()


def search(query: str, k: int = 5) -> list[str]:
    """Keyword search (any word matches), best first."""
    words = [w for w in re.findall(r"\w+", query) if len(w) > 2]
    if not words:
        return []
    return [r[0] for r in _db().execute("SELECT path FROM fts WHERE fts MATCH ? ORDER BY rank LIMIT ?", (" OR ".join(words), k))]


def links(path: str) -> list[str]:
    return [r[0] for r in _db().execute("SELECT dst FROM links WHERE src=?", (path,))]


def list_notes(suffix: str = ".md", prefix: str = "") -> list[str]:
    out = []
    for root, dirs, files in os.walk(os.path.join(VAULT, prefix)):
        dirs[:] = [d for d in dirs if d != ".git"]
        out += [os.path.relpath(os.path.join(root, f), VAULT) for f in files if f.endswith(suffix)]
    return sorted(out)


def last_commit(path: str) -> str | None:
    commits = list(_repo.iter_commits(paths=path, max_count=1))
    return commits[0].hexsha[:8] if commits else None


def main() -> None:
    from mcp.server.fastmcp import FastMCP
    init(os.environ.get("GLACIER_VAULT", "vault"))
    mcp = FastMCP("glacier-memory")

    @mcp.tool(name="write_note")
    def _write(path: str, body: str, author: str = "worker:unknown", run_id: str = "", agent: str | None = None) -> str:
        """Create or replace a shared note. Supply author worker:<model> and the current run id."""
        who = author if agent is None else agent  # agent is accepted for older MCP clients.
        return f"saved {path} (commit {write_note(path, body, author=who, run_id=run_id)})"

    @mcp.tool(name="search")
    def _search(query: str, k: int = 10) -> str:
        """Keyword search of the shared vault (any word matches). Returns matching note paths, best first."""
        return json.dumps(search(query, k))

    @mcp.tool(name="links")
    def _links(path: str) -> str:
        """Notes this note links to with [[wiki links]]."""
        return json.dumps(links(path))

    @mcp.tool(name="read_note")
    def _read(path: str) -> str:
        """Read a note from the shared vault."""
        return read_note(path)

    mcp.run()


if __name__ == "__main__":
    main()
