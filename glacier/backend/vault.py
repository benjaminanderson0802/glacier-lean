"""Glacier memory vault: markdown/JSON notes tracked in git + SQLite keyword search + event log.
Importable (call init(path) once) and runnable as an MCP server: `python vault.py` (uses GLACIER_VAULT, default ./vault).
Every write is: atomic file write -> git commit -> index update. No AI models."""
import os, re, json, sqlite3, tempfile, threading
import git

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


def write_note(path: str, body: str, agent: str = "unknown") -> str:
    """Create or replace a note; returns the short commit sha."""
    full = safe_path(path)
    with _lock:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(full))
        os.write(fd, body.encode()); os.close(fd); os.replace(tmp, full)
        _repo.index.add([os.path.relpath(full, VAULT)])
        sha = _repo.index.commit(f"[{agent}] write {path}").hexsha[:8]
        c = _db()
        c.execute("DELETE FROM fts WHERE path=?", (path,)); c.execute("INSERT INTO fts VALUES (?,?)", (path, body))
        c.execute("DELETE FROM links WHERE src=?", (path,))
        for dst in re.findall(r"\[\[([^\]|#]+)", body):
            c.execute("INSERT INTO links VALUES (?,?)", (path, dst.strip()))
        c.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)", (agent, "write_note", json.dumps({"path": path, "commit": sha})))
        c.commit(); c.close()
    return sha


def read_note(path: str) -> str:
    with open(safe_path(path)) as f:
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
    def _write(path: str, body: str, agent: str = "unknown") -> str:
        """Create or replace a markdown note in the shared vault (path like projects/x.md)."""
        return f"saved {path} (commit {write_note(path, body, agent)})"

    @mcp.tool(name="search")
    def _search(query: str, k: int = 5) -> str:
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
