"""Glacier memory vault: markdown/JSON notes tracked in git + SQLite keyword search + event log.
Importable (call init(path) once) and runnable as an MCP server: `python vault.py` (uses GLACIER_VAULT, default ./vault).
Every write is: atomic file write -> git commit -> index update. No AI models."""
# Git access policy: all operations using the process-wide `_repo` hold `_lock`.
# The lock serializes GitPython's index and persistent cat-file helpers. Operations
# that also take a workspace merge lock must acquire `_lock` first, then merge locks.
import os, re, json, sqlite3, tempfile, threading, time
import git
import memory_meta

VAULT: str = ""
_repo = None
_note_history_cache: dict[str, tuple[tuple[int | None, int | None], list[dict]]] = {}
_note_history_cache_lock = threading.Lock()
_note_history_generation: dict[str, int] = {}
_note_history_inflight: dict[str, int] = {}
class FairRLock:
    """A re-entrant lock that serves waiting threads in arrival order.

    threading.RLock lets a busy reader re-take the lock again and again while a
    save keeps waiting; on slower machines (seen on Windows) saves then waited
    past 10 s. First come, first served bounds every wait.
    """

    def __init__(self):
        self._cond = threading.Condition(threading.Lock())
        self._owner = None
        self._depth = 0
        self._next_ticket = 0
        self._serving = 0
        self._abandoned: set[int] = set()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        me = threading.get_ident()
        with self._cond:
            if self._owner == me:
                self._depth += 1
                return True
            if not blocking and (self._owner is not None or self._serving != self._next_ticket):
                return False
            ticket = self._next_ticket
            self._next_ticket += 1
            deadline = None if timeout is None or timeout < 0 else time.monotonic() + timeout
            while self._owner is not None or self._serving != ticket:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    # Give up our place without blocking the threads behind us.
                    self._abandoned.add(ticket)
                    self._skip_abandoned()
                    self._cond.notify_all()
                    return False
                self._cond.wait(remaining)
            self._owner, self._depth = me, 1
            self._serving += 1
            self._skip_abandoned()
            return True

    def _skip_abandoned(self) -> None:
        while self._serving in self._abandoned:
            self._abandoned.discard(self._serving)
            self._serving += 1

    def release(self) -> None:
        with self._cond:
            if self._owner != threading.get_ident():
                raise RuntimeError("cannot release a lock this thread does not hold")
            self._depth -= 1
            if self._depth == 0:
                self._owner = None
                self._cond.notify_all()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


_lock = FairRLock()
_note_metadata_cache: dict[str, tuple[int, int, dict, str]] = {}
_note_metadata_cache_lock = threading.Lock()


def init(path: str) -> None:
    global VAULT, _repo
    VAULT = os.path.abspath(path)
    with _note_metadata_cache_lock:
        _note_metadata_cache.clear()
    with _note_history_cache_lock:
        _note_history_cache.clear()
        _note_history_generation.clear()
        _note_history_inflight.clear()
    os.makedirs(VAULT, exist_ok=True)
    _repo = git.Repo.init(VAULT)
    with open(os.path.join(VAULT, ".gitignore"), "w") as f:
        f.write(".index.sqlite*\n")
    # WAL keeps readers from holding up index commits. FULL sync remains enabled:
    # this SQLite file is rebuildable, but writes should still be durable.
    index_path = os.path.join(VAULT, ".index.sqlite")
    with sqlite3.connect(index_path, timeout=30) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(path UNINDEXED, body)")
        c.execute("CREATE TABLE IF NOT EXISTS links(src TEXT, dst TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS events(ts DEFAULT CURRENT_TIMESTAMP, agent TEXT, kind TEXT, data TEXT)")


def _db():
    c = sqlite3.connect(os.path.join(VAULT, ".index.sqlite"), timeout=30)
    c.execute("PRAGMA synchronous=FULL")
    return c


def invalidate_note_history(paths) -> None:
    """Clear cached git history for paths changed by a multi-note transaction."""
    with _note_history_cache_lock:
        for path in paths:
            relative = str(path).replace("\\", "/")
            if relative in _note_history_inflight:
                _note_history_generation[relative] = _note_history_generation.get(relative, 0) + 1
            _note_history_cache.pop(relative, None)


def _history_lookup_done(path: str) -> None:
    if _note_history_inflight[path] == 1:
        _note_history_inflight.pop(path, None)
        _note_history_generation.pop(path, None)
    else:
        _note_history_inflight[path] -= 1


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
    """Saved versions of one note, newest first, cached until that note is written.

    Git log uses a separate process so it does not share GitPython's persistent
    cat-file pipe. Repeated history reads reuse the result; a write to this note
    invalidates it after the new commit is created.
    """
    full = safe_path(path)
    relative = os.path.relpath(full, VAULT).replace(os.sep, "/")
    try:
        stat = os.stat(full)
        version = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        version = (None, None)
    with _note_history_cache_lock:
        cached = _note_history_cache.get(relative)
        if cached is not None and cached[0] == version:
            return [dict(entry) for entry in cached[1]]
        generation = _note_history_generation.get(relative, 0)
        _note_history_inflight[relative] = _note_history_inflight.get(relative, 0) + 1
    try:
        output = git.Git(VAULT).log("--format=%H%x1f%an%x1f%cI%x1f%B%x1e", "--", relative)
    except Exception:
        with _note_history_cache_lock:
            _history_lookup_done(relative)
        raise
    entries = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, date, message = (record.split("\x1f", 3) + ["", "", ""])[:4]
        entries.append({"sha": sha, "author": author, "date": date, "message": message.strip()})
    try:
        stat = os.stat(full)
        current_version = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        current_version = (None, None)
    with _note_history_cache_lock:
        if (_note_history_generation.get(relative, 0) == generation and current_version == version):
            _note_history_cache[relative] = (version, entries)
            if len(_note_history_cache) > 512:
                _note_history_cache.pop(next(iter(_note_history_cache)))
        _history_lookup_done(relative)
    return [dict(entry) for entry in entries]


def _plain(path: str) -> str:
    """Drop Windows' extended-length prefix.

    realpath keeps "\\\\?\\" when it cannot confirm the short form, which happens while
    another save is replacing a file in the same folder; the path is the same place.
    """
    if os.name == "nt":
        if path.startswith("\\\\?\\UNC\\"):
            return "\\\\" + path[8:]
        if path.startswith("\\\\?\\"):
            return path[4:]
    return path


def _is_git_metadata_path(path: str) -> bool:
    """Match Git metadata directories across Windows separators and case-insensitive filesystems."""
    portable = path.replace("\\", "/").casefold()
    return "/.git/" in f"/{portable.strip('/')}/"


_roots_cache: tuple[str, tuple[str, ...]] = ("", ())


def _vault_roots() -> tuple[str, ...]:
    """The vault folder as given and as resolved, computed once per vault (realpath is slow on Windows)."""
    global _roots_cache
    if _roots_cache[0] != VAULT:
        _roots_cache = (VAULT, tuple({os.path.normcase(VAULT), os.path.normcase(_plain(os.path.realpath(VAULT)))}))
    return _roots_cache[1]


def safe_path(path: str) -> str:
    """Absolute path inside the vault; raises ValueError on escapes like ../"""
    if os.name == "nt":
        path = path.replace("\\", "/")
    full = _plain(os.path.realpath(os.path.join(VAULT, path)))
    # Compare without case on Windows/macOS-style paths, and accept the vault's own
    # resolved location too (realpath can report different casing than abspath).
    norm = os.path.normcase(full)
    for root in _vault_roots():
        if root and norm.startswith(root + os.sep):
            if _is_git_metadata_path(norm[len(root):]):
                break
            return full
    raise ValueError(f"bad vault path: {path}")


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
        history_path = os.path.relpath(full, VAULT).replace(os.sep, "/")
        invalidate_note_history([history_path])
        # Run change reads are cached per run id. Owner and API writes unrelated
        # to a run do not invalidate that run's result.
        try:
            import rollback
            cached_run_id = metadata_run_id or (writer[4:] if writer.startswith("run:") else "")
            rollback.invalidate_vault_change_cache(cached_run_id, git_writer, history_path)
        except ImportError:
            pass
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


def read_note_metadata_with_stat(path: str) -> tuple[dict, str, os.stat_result]:
    """Return metadata, body and the validating stat, reusing parsed data when possible."""
    full = safe_path(path)
    stat = os.stat(full)
    with _note_metadata_cache_lock:
        cached = _note_metadata_cache.get(path)
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2], cached[3], stat
    with open(full, encoding="utf-8") as f:
        text = f.read()
    meta, body = memory_meta.parse(text, path)
    with _note_metadata_cache_lock:
        _note_metadata_cache[path] = (stat.st_mtime_ns, stat.st_size, meta, body)
    return meta, body, stat


def read_note_metadata(path: str) -> tuple[dict, str]:
    """Return parsed note metadata/body, reusing it while the file mtime is unchanged."""
    meta, body, _ = read_note_metadata_with_stat(path)
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
