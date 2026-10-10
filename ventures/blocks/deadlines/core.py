from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _database_path() -> Path:
    return Path(os.environ.get("GLACIER_HOME", str(Path.home() / ".glacier"))) / "ventures" / "deadlines.db"


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
      CREATE TABLE IF NOT EXISTS deadline_items (
        item_id TEXT PRIMARY KEY, start_date TEXT NOT NULL, rule TEXT NOT NULL,
        label TEXT NOT NULL, created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS deadline_firings (
        item_id TEXT NOT NULL, milestone TEXT NOT NULL, due_date TEXT NOT NULL,
        fired_at TEXT NOT NULL, PRIMARY KEY(item_id, milestone, due_date));
    """)
    return con


def _date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _validate_rule(rule: str) -> None:
    if re.fullmatch(r"\d+d(?:\|\d+d)*", rule):
        if any(int(part[:-1]) < 0 for part in rule.split("|")):
            raise ValueError("unsupported deadline rule: offsets must be nonnegative")
        return
    if rule.lower() == "jan2-mar2":
        return
    pieces = rule.split("|")
    if len(pieces) == 2:
        try:
            start, end = map(date.fromisoformat, pieces)
            if end < start:
                raise ValueError
            return
        except ValueError:
            pass
    raise ValueError(f"unsupported deadline rule: {rule!r}")


def add(item_id: str, start_date: str, rule: str, label: str) -> None:
    """Insert or replace one deadline definition; rule dates are local calendar dates."""
    _date(start_date)
    _validate_rule(rule)
    if not item_id.strip() or not label.strip():
        raise ValueError("item_id and label are required")
    with _connect() as con:
        con.execute("INSERT INTO deadline_items(item_id,start_date,rule,label,created_at) VALUES(?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET start_date=excluded.start_date, rule=excluded.rule, label=excluded.label", (item_id, start_date, rule, label, datetime.now(timezone.utc).isoformat()))


def _events(start_date: date, rule: str) -> list[tuple[str, date]]:
    if re.fullmatch(r"\d+d(?:\|\d+d)*", rule):
        return [("reminder", start_date + timedelta(days=int(part[:-1]))) for part in rule.split("|")]
    if rule.lower() == "jan2-mar2":
        year = start_date.year
        if start_date > date(year, 3, 2):
            year += 1
        first, last = date(year, 1, 2), date(year, 3, 2)
        return [("window_open", first), ("window_close", last)]
    first, last = map(date.fromisoformat, rule.split("|"))
    # A fixed tenth-day nudge gives a useful early check-in across short and
    # long county windows; clamp it before the closing date for short windows.
    nudge = min(first + timedelta(days=10), last - timedelta(days=1))
    return [("window_open", first), ("due_soon", nudge), ("window_close", last)]


def glacier_steps(item_id: str, label: str, milestone: str, due_date: str) -> list[dict[str, Any]]:
    """Return a durable Glacier note and native approval node for a reminder."""
    prompt = f"Review deadline: {label} is {milestone.replace('_', ' ')} on {due_date}. Mark this reminder acknowledged?"
    safe_id = hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:16]
    return [
        {
            "type": "note",
            "config": {
                "path": f"ventures/deadline-reminders/{safe_id}-{due_date}.md",
                "template": f"# {label}\n\n{milestone.replace('_', ' ').capitalize()} on {due_date}.\n\n{{summary}}",
            },
        },
        {"type": "approval", "config": {"prompt": prompt}},
    ]


def due(on_date: str | date) -> list[dict[str, Any]]:
    """Return reminders exactly on ``on_date`` and atomically mark each as fired."""
    day = _date(on_date)
    fired_at = datetime.now(timezone.utc).isoformat()
    result: list[dict[str, Any]] = []
    with _connect() as con:
        items = con.execute("SELECT item_id,start_date,rule,label FROM deadline_items ORDER BY item_id").fetchall()
        for item_id, start, rule, label in items:
            for milestone, due_day in _events(date.fromisoformat(start), rule):
                due_string = due_day.isoformat()
                if due_day != day:
                    continue
                cursor = con.execute("INSERT OR IGNORE INTO deadline_firings(item_id,milestone,due_date,fired_at) VALUES(?,?,?,?)", (item_id, milestone, due_string, fired_at))
                if not cursor.rowcount:
                    continue
                result.append({"item_id": item_id, "label": label, "rule": rule, "date": due_string, "milestone": milestone, "glacier_steps": glacier_steps(item_id, label, milestone, due_string)})
    return result
