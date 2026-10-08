"""Append-only audit events for consequential Glacier runtime effects."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone


def _path(home: str | None = None) -> str:
    # Keep audit writes out of the runner and DBOS state database. That file is
    # on the scheduler's critical path and extra SQLite contention can delay slots.
    return os.path.join(os.path.abspath(home or os.environ.get("GLACIER_HOME", "data")), "audit.sqlite")


def record(event_type: str, *, who: str = "owner", what: dict | None = None) -> None:
    """Record a redacted, structured effect summary; callers must never pass secret values."""
    path = _path()
    try:
        # Direct runner calls and first-use routes may precede app startup. Create
        # the configured home only when an audit write actually needs the store.
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = json.dumps(what or {}, sort_keys=True, ensure_ascii=False)
        # Many API requests can record effects at once (for example, a burst of
        # memory writes). Give SQLite enough time to serialize those short
        # transactions instead of dropping audit events under ordinary load.
        with sqlite3.connect(path, timeout=30) as connection:
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("""CREATE TABLE IF NOT EXISTS glacier_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                who TEXT NOT NULL,
                what TEXT NOT NULL,
                happened_at TEXT NOT NULL
            )""")
            connection.execute("INSERT INTO glacier_audit(event_type,who,what,happened_at) VALUES (?,?,?,?)",
                               (event_type, who, payload, datetime.now(timezone.utc).isoformat(timespec="milliseconds")))
    except Exception:
        # Audit storage is best-effort at the call boundary: an unavailable
        # audit database must never turn a successful side effect into failure.
        logging.getLogger(__name__).warning("Could not write audit event %s", event_type, exc_info=True)


def events(event_type: str | None = None, *, home: str | None = None) -> list[dict]:
    with sqlite3.connect(_path(home), timeout=30) as connection:
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute("SELECT event_type,who,what,happened_at FROM glacier_audit ORDER BY id").fetchall()
        except sqlite3.OperationalError:
            return []
    result = [{"event_type": r["event_type"], "who": r["who"], "what": json.loads(r["what"]), "when": r["happened_at"]}
              for r in rows]
    return [row for row in result if row["event_type"] == event_type] if event_type else result
