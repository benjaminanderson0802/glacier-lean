"""Glacier memory vault: markdown/JSON notes tracked in git + SQLite keyword search + event log.
Importable (call init(path) once) and runnable as an MCP server: `python vault.py` (uses GLACIER_VAULT, default ./vault).
Every write is: atomic file write -> git commit -> index update. No AI models."""
# Git access policy: all operations using the process-wide `_repo` hold `_lock`.
# The lock serializes GitPython's index and persistent cat-file helpers. Operations
# that also take a workspace merge lock must acquire `_lock` first, then merge locks.
import os, re, json, sqlite3, tempfile, threading
import git
import memory_meta

VAULT: str = ""
_repo = None
_lock = threading.RLock()
_note_metadata_cache: dict[str, tuple[int, int, dict, str]] = {}
_note_metadata_cache_lock = threading.Lock()


def init(path: str) -> None:
    global VAULT, _repo
    VAULT = os.path.abspath(path)
    with _note_metadata_cache_lock:
        _note_metadata_cache.clear()
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


def replace_file(source: str, destination: str, attempts: int = 100, delay: float = 0.02) -> None:
    """os.replace, retried briefly on Windows while another thread or app has the file open.

    Windows refuses to replace a file that is open for reading ("Access is denied"); readers
    hold notes only for a moment, so wait for them instead of failing the save.
    """
    import time
    for attempt in range(attempts):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if os.name != "nt" or attempt == attempts - 1:
                raise
            time.sleep(delay)


def note_history(path: str) -> list[dict]:
    """Saved versions of one note, newest first, read by a separate git process.

    This does not use the shared repository object, so it needs no vault lock and
    never makes note saves wait while a long history is read.
    """
    full = safe_path(path)
    relative = os.path.relpath(full, VAULT).replace(os.sep, "/")
    output = git.Git(VAULT).log("--format=%H%x1f%an%x1f%cI%x1f%B%x1e", "--", relative)
    entries = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, date, message = (record.split("\x1f", 3) + ["", "", ""])[:4]
        entries.append({"sha": sha, "author": author, "date": date, "message": message.strip()})
    return entries


def safe_path(path: str) -> str:
    """Absolute path inside the vault; raises ValueError on escapes like ../"""
    if os.name == "nt":
        path = path.replace("\\", "/")
    full = os.path.realpath(os.path.join(VAULT, path))
    if not full.startswith(VAULT + os.sep) or "/.git/" in full + "/":
        raise ValueError(f"bad vault path: {path}")
    return full


def write_note(path: str, body: str, agent: str = "unknown", *, author: str | None = None, run_id: str = "") -> str:
    """Create or replace a note; returns the short commit sha. Legacy agent callers remain supported."""
    if os.name == "nt":
        path = path.replace("\\", "/")
    full = safe_path(path)
    if run_id and not re.fullmatch(r"[A-Za-z0-9-]{1,64}", run_id):
        raise ValueError("Run id must contain only letters, numbers, and hyphens (up to 64 characters)")
    if author and author.startswith("worker:") and not re.fullmatch(r"worker:[A-Za-z0-9._-]{1,64}", author):
        raise ValueError("Worker author must be worker:<model> using letters, numbers, dot, underscore, or hyphen")
    with _lock:
        previous = None
        try:
            with open(full, encoding="utf-8") as f:
                previous = f.read()
        except FileNotFoundError:
            pass
        # Keep the historical `agent=` call shape, while run note steps carry an
        # explicit run identity in the service-owned author field.
        metadata_run_id = run_id
        if path.startswith("runs/") and not metadata_run_id and agent == "glacier-runner":
            match = re.search(r"(?<![a-f0-9])([a-f0-9]{12})(?![a-f0-9])", path + "\n" + body, re.I)
            if match:
                metadata_run_id = match.group(1)
        if path.endswith(".md") and not metadata_run_id and author is None and agent != "unknown":
            incoming = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", body, re.S)
            if incoming:
                run_line = re.search(r"(?m)^run_id:\s*(.*)$", incoming.group(1))
                if run_line:
                    metadata_run_id = run_line.group(1).strip().strip('"')
        writer = author or (f"run:{metadata_run_id}" if metadata_run_id and agent == "glacier-runner" else
                            f"run:{run_id}" if run_id else agent)
        stored_body = memory_meta.render(path, body, writer, metadata_run_id, previous)[1] if path.endswith(".md") else body
        os.makedirs(os.path.dirname(full), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(full))
        os.write(fd, stored_body.encode()); os.close(fd); replace_file(tmp, full)
        git_writer = "glacier-runner" if agent == "glacier-runner" else writer
        message_writer = f"run:{metadata_run_id}" if agent == "glacier-runner" and metadata_run_id else writer
        message = f"[{message_writer}] write {path}"
        if agent == "glacier-runner" and metadata_run_id:
            message += f" [run:{metadata_run_id}]"
        actor = git.Actor(git_writer, "glacier@localhost")
        _repo.index.add([os.path.relpath(full, VAULT)])
        sha = _repo.index.commit(message, author=actor, committer=actor).hexsha[:8]
        try:
            stat = os.stat(full)
            parsed_meta, parsed_body = memory_meta.parse(stored_body, path)
            cached = (stat.st_mtime_ns, stat.st_size, parsed_meta, parsed_body)
            with _note_metadata_cache_lock:
                _note_metadata_cache[path] = cached
        except OSError:
            with _note_metadata_cache_lock:
                _note_metadata_cache.pop(path, None)
        # Keep bookkeeping ordered with commits: an earlier writer must not
        # overwrite the index state recorded by a later Git commit.
        c = _db()
        try:
            indexed_body = memory_meta.parse(stored_body, path)[1] if path.endswith(".md") else stored_body
            c.execute("DELETE FROM fts WHERE path=?", (path,)); c.execute("INSERT INTO fts VALUES (?,?)", (path, indexed_body))
            c.execute("DELETE FROM links WHERE src=?", (path,))
            for dst in re.findall(r"\[\[([^\]]+)\]\]", body):
                c.execute("INSERT INTO links VALUES (?,?)", (path, dst.split("|", 1)[0].strip().removesuffix(".md")))
            c.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)", (writer, "write_note", json.dumps({"path": path, "commit": sha})))
            c.commit()
        finally:
            c.close()
    try:
        import store
        event = {"type": "memory", "path": path,
                 "change": "created" if previous is None else "updated",
                 "author": writer, "run_id": metadata_run_id or ""}
        if writer.startswith("run:"):
            # A run's note event follows its node events; a short delay keeps that order for live screens.
            threading.Timer(0.1, store.broadcaster.publish, args=(event,)).start()
        else:
            store.broadcaster.publish(event)
    except (ImportError, AttributeError):
        pass
    return sha


def read_note_metadata(path: str) -> tuple[dict, str]:
    """Return parsed note metadata/body, reusing it while the file mtime is unchanged."""
    full = safe_path(path)
    stat = os.stat(full)
    with _note_metadata_cache_lock:
        cached = _note_metadata_cache.get(path)
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2], cached[3]
    with open(full, encoding="utf-8") as f:
        text = f.read()
    meta, body = memory_meta.parse(text, path)
    with _note_metadata_cache_lock:
        _note_metadata_cache[path] = (stat.st_mtime_ns, stat.st_size, meta, body)
    return meta, body


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
        out += [os.path.relpath(os.path.join(root, f), VAULT).replace(os.sep, "/") for f in files if f.endswith(suffix)]
    return sorted(out)


def last_commit(path: str) -> str | None:
    with _lock:
        commits = list(_repo.iter_commits(paths=path, max_count=1))
    return commits[0].hexsha[:8] if commits else None


def main() -> None:
    # MCP is implemented in mem_server.py; this entry point remains for older launchers.
    import mem_server
    mem_server.main()


if __name__ == "__main__":
    main()
