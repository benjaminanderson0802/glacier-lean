"""Glacier memory service (basic): markdown vault tracked in git + SQLite keyword search + event log, as MCP tools.
Only this process writes the vault: atomic file write -> git commit -> index update. No AI models needed."""
import os, re, json, sqlite3, tempfile
import git
from mcp.server.fastmcp import FastMCP

VAULT = os.path.abspath(os.environ.get("GLACIER_VAULT", "vault"))
DB = os.path.join(VAULT, ".index.sqlite")
os.makedirs(VAULT, exist_ok=True)
repo = git.Repo.init(VAULT)
with open(os.path.join(VAULT, ".gitignore"), "w") as f:
    f.write(".index.sqlite*\n")

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, body)")
    c.execute("CREATE TABLE IF NOT EXISTS links(src TEXT, dst TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS events(ts DEFAULT CURRENT_TIMESTAMP, agent TEXT, kind TEXT, data TEXT)")
    return c

mcp = FastMCP("glacier-memory")

@mcp.tool()
def write_note(path: str, body: str, agent: str = "unknown") -> str:
    """Create or replace a markdown note in the shared vault (path like projects/x.md)."""
    full = os.path.join(VAULT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(full))
    os.write(fd, body.encode()); os.close(fd); os.replace(tmp, full)
    repo.index.add([path])
    sha = repo.index.commit(f"[{agent}] write {path}").hexsha[:8]
    c = db()
    c.execute("DELETE FROM fts WHERE path=?", (path,)); c.execute("INSERT INTO fts VALUES (?,?)", (path, body))
    c.execute("DELETE FROM links WHERE src=?", (path,))
    for dst in re.findall(r"\[\[([^\]|#]+)", body):
        c.execute("INSERT INTO links VALUES (?,?)", (path, dst.strip()))
    c.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)", (agent, "write_note", json.dumps({"path": path, "commit": sha})))
    c.commit()
    return f"saved {path} (commit {sha})"

@mcp.tool()
def search(query: str, k: int = 5) -> str:
    """Keyword search of the shared vault (any word matches). Returns matching note paths, best first."""
    words = [w for w in re.findall(r"\w+", query) if len(w) > 2]
    if not words:
        return "[]"
    rows = db().execute("SELECT path FROM fts WHERE fts MATCH ? ORDER BY rank LIMIT ?", (" OR ".join(words), k))
    return json.dumps([r[0] for r in rows])

@mcp.tool()
def links(path: str) -> str:
    """Notes this note links to with [[wiki links]]."""
    return json.dumps([r[0] for r in db().execute("SELECT dst FROM links WHERE src=?", (path,))])

@mcp.tool()
def read_note(path: str) -> str:
    """Read a note from the shared vault."""
    return open(os.path.join(VAULT, path)).read()

if __name__ == "__main__":
    mcp.run()
