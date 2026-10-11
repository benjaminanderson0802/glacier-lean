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
import nodes.email_read as email_read


_stop = threading.Event()
_thread = None
_email_thread = None


def _db_path(home: str) -> str:
    return os.path.join(home, "triggers.sqlite")


def _connect(home: str):
    conn = sqlite3.connect(_db_path(home), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("CREATE TABLE IF NOT EXISTS handled_files (env_id TEXT, node_id TEXT, path TEXT, handled_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(env_id,node_id,path))")
    conn.execute("CREATE TABLE IF NOT EXISTS email_trigger_state (env_id TEXT, node_id TEXT, initialized INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(env_id,node_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS handled_emails (env_id TEXT, node_id TEXT, message_id TEXT, handled_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(env_id,node_id,message_id))")
    return conn


def scan_email_once(home: str) -> int:
    """Poll enabled email triggers; the first poll records current mail without replaying history."""
    started = 0
    for note in vault.list_notes(".json", "environments"):
        try:
            env = json.loads(vault.read_note(note))
            if not _enabled(env):
                continue
            for node in env.get("nodes", []):
                if node.get("type") != "email_trigger":
                    continue
                result = email_read.run({"config": node.get("config") or {}, "home": home, "env_id": env["id"],
                    "run_id": "", "node_id": node["id"], "prev": None, "workspace": ""})
                if result.get("state") != "done":
                    continue
                messages = json.loads(result.get("output") or "[]")
                if not isinstance(messages, list):
                    continue
                with _connect(home) as conn:
                    state = conn.execute("SELECT initialized FROM email_trigger_state WHERE env_id=? AND node_id=?",
                                         (env["id"], node["id"])).fetchone()
                    initialized = bool(state and state[0])
                    if not initialized:
                        for message in messages:
                            if isinstance(message, dict):
                                message_id = str(message.get("message_id") or json.dumps(message, sort_keys=True))
                                conn.execute("INSERT OR IGNORE INTO handled_emails(env_id,node_id,message_id) VALUES(?,?,?)",
                                             (env["id"], node["id"], message_id))
                        conn.execute("INSERT INTO email_trigger_state(env_id,node_id,initialized) VALUES(?,?,1) "
                                     "ON CONFLICT(env_id,node_id) DO UPDATE SET initialized=1", (env["id"], node["id"]))
                        continue
                    fresh = []
                    for message in messages:
                        if not isinstance(message, dict):
                            continue
                        message_id = str(message.get("message_id") or json.dumps(message, sort_keys=True))
                        if not conn.execute("SELECT 1 FROM handled_emails WHERE env_id=? AND node_id=? AND message_id=?",
                                            (env["id"], node["id"], message_id)).fetchone():
                            fresh.append((message_id, message))
                for message_id, message in fresh:
                    stable = uuid.uuid5(uuid.NAMESPACE_URL, f"glacier-email:{env['id']}:{node['id']}:{message_id}").hex[:12]
                    trigger = {"type": "email", "node_id": node["id"], "body": message}
                    runner.start_run(env["id"], {"_trigger": trigger}, run_id=stable)
                    with _connect(home) as conn:
                        conn.execute("INSERT OR IGNORE INTO handled_emails(env_id,node_id,message_id) VALUES(?,?,?)",
                                     (env["id"], node["id"], message_id))
                    started += 1
        except (OSError, ValueError, KeyError, json.JSONDecodeError, sqlite3.Error):
            continue
    return started


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


def _email_poll_loop(home: str) -> None:
    interval = max(30.0, min(float(os.environ.get("GLACIER_EMAIL_POLL_SECONDS", "60")), 3600.0))
    while not _stop.is_set():
        try:
            scan_email_once(home)
        except Exception:
            pass
        _stop.wait(interval)


def start(home: str) -> None:
    global _thread, _email_thread
    if _thread and _thread.is_alive():
        return
    rebuild_handled_files(home)
    _stop.clear()
    _thread = threading.Thread(target=_poll_loop, args=(home,), name="glacier-file-triggers", daemon=True)
    _thread.start()
    _email_thread = threading.Thread(target=_email_poll_loop, args=(home,), name="glacier-email-triggers", daemon=True)
    _email_thread.start()


def stop() -> None:
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2)
    if _email_thread and _email_thread.is_alive():
        _email_thread.join(timeout=2)
