"""Local file trigger polling and durable handled-file records."""

import fnmatch
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

import runner
import store
import vault
from nodes.file_trigger import validate_folder


_stop = threading.Event()
_thread = None


def _db_path(home: str) -> str:
    return os.path.join(home, "triggers.sqlite")


def _connect(home: str):
    conn = sqlite3.connect(_db_path(home), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("CREATE TABLE IF NOT EXISTS handled_files (env_id TEXT, node_id TEXT, path TEXT, handled_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(env_id,node_id,path))")
    return conn


def claim_file(home: str, env_id: str, node_id: str, path: str) -> bool:
    """Claim a file once across processes and restarts, before starting its run."""
    with _connect(home) as conn:
        cur = conn.execute("INSERT OR IGNORE INTO handled_files(env_id,node_id,path) VALUES(?,?,?)", (env_id, node_id, path))
        return cur.rowcount == 1


def rebuild_handled_files(home: str) -> None:
    """Rebuild the polling index from durable run snapshots if it is missing or was removed."""
    with _connect(home) as conn:
        for item in store.list_runs(None):
            try:
                trigger = store.graph_of(item["run_id"]).get("_trigger") or {}
            except (KeyError, TypeError):
                continue
            if trigger.get("type") == "file" and trigger.get("file") and trigger.get("node_id"):
                conn.execute("INSERT OR IGNORE INTO handled_files(env_id,node_id,path) VALUES(?,?,?)",
                             (item["env_id"], trigger["node_id"], trigger["file"]))


def _enabled(env: dict) -> bool:
    return env.get("enabled", True) is not False


def _native_absolute_path(path: str | os.PathLike) -> str:
    """Return a stable native absolute spelling for trigger attribution and keys.

    A folder can be supplied through Git Bash as ``/c/Users/...`` even when
    Python is running on Windows. Convert that spelling before resolving it so
    the run snapshot and restart de-duplication use the same native path.
    """
    value = os.fspath(path)
    if os.name == "nt":
        normalized = value.replace("\\", "/")
        if len(normalized) >= 3 and normalized[0] == "/" and normalized[1].isalpha() and normalized[2] == "/":
            value = normalized[1].upper() + ":\\" + normalized[3:].replace("/", "\\")
    return str(Path(value).expanduser().resolve())


def scan_once(home: str) -> int:
    """Find unhandled files and start one normal run for each matching file."""
    started = 0
    for note in vault.list_notes(".json", "environments"):
        try:
            env = json.loads(vault.read_note(note))
            if not _enabled(env):
                continue
            for node in env.get("nodes", []):
                if node.get("type") != "file_trigger":
                    continue
                config = node.get("config") or {}
                folder = validate_folder(config.get("folder"), home)
                pattern = str(config.get("pattern") or "*")
                for name in sorted(os.listdir(folder)):
                    path = folder / name
                    try:
                        if not path.is_file() or not fnmatch.fnmatch(name, pattern):
                            continue
                        resolved = _native_absolute_path(path.resolve(strict=True))
                    except OSError:
                        continue
                    with _connect(home) as conn:
                        handled = conn.execute("SELECT 1 FROM handled_files WHERE env_id=? AND node_id=? AND path=?",
                                               (env["id"], node["id"], resolved)).fetchone()
                    if not handled:
                        trigger = {"type": "file", "node_id": node["id"], "file": resolved}
                        # The stable id plus the run snapshot lets startup rebuild the index if a crash
                        # lands after the run was recorded but before its handled row was written.
                        stable = uuid.uuid5(uuid.NAMESPACE_URL, f"glacier-file:{env['id']}:{node['id']}:{resolved}").hex[:12]
                        runner.start_run(env["id"], {"_trigger": trigger}, run_id=stable)
                        claim_file(home, env["id"], node["id"], resolved)
                        started += 1
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            # A bad folder setting cannot crash the watcher or block other flows.
            continue
    return started


def _poll_loop(home: str) -> None:
    interval = max(0.1, min(float(os.environ.get("GLACIER_TRIGGER_POLL_SECONDS", "1")), 60.0))
    while not _stop.is_set():
        try:
            scan_once(home)
        except Exception:
            # Poll again on the next tick; trigger errors are not allowed to stop the backend.
            pass
        _stop.wait(interval)


def start(home: str) -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    rebuild_handled_files(home)
    _stop.clear()
    _thread = threading.Thread(target=_poll_loop, args=(home,), name="glacier-file-triggers", daemon=True)
    _thread.start()


def stop() -> None:
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2)
