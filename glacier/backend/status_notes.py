"""Plain-language flow status notes rendered only from saved environments and run records."""
import json
import sqlite3
from datetime import datetime
from decimal import Decimal

import runner
import store
import vault


AUTHOR = "glacier-status"


def _db_path() -> str:
    return store.DB


def _flow_name(env_id: str, runs: list[dict]) -> str:
    try:
        return runner.load_env(env_id).get("name") or env_id
    except (FileNotFoundError, ValueError):
        if runs:
            try:
                return json.loads(runs[0]["graph"]).get("name") or env_id
            except (TypeError, json.JSONDecodeError):
                pass
        return env_id


def _date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return value or "Time not recorded"


def _money(value) -> str:
    """Render the stored SQLite numeric value without rounding away recorded precision."""
    amount = Decimal(str(value or 0))
    return f"${format(amount, 'f')}"


def _runs_for(env_id: str) -> tuple[list[dict], Decimal]:
    with sqlite3.connect(_db_path()) as db:
        db.row_factory = sqlite3.Row
        all_rows = db.execute("""SELECT run_id, status, started_at, graph FROM glacier_runs
                                WHERE env_id=? ORDER BY started_at DESC, rowid DESC""", (env_id,)).fetchall()
        rows = all_rows[:10]
        result = []
        total = Decimal(0)
        for row in all_rows:
            usage = db.execute("SELECT model, route, cost_usd FROM glacier_usage WHERE run_id=?", (row["run_id"],)).fetchall()
            total += sum((Decimal(str(u["cost_usd"] or 0)) for u in usage), Decimal(0))
        for row in rows:
            graph = json.loads(row["graph"] or "{}")
            labels = {n.get("id"): (n.get("label") or n.get("name") or n.get("id")) for n in graph.get("nodes", [])}
            failed = db.execute("""SELECT node_id FROM glacier_nodes WHERE run_id=? AND state='failed'
                                  ORDER BY rowid LIMIT 1""", (row["run_id"],)).fetchone()
            usage = db.execute("SELECT model, route, cost_usd FROM glacier_usage WHERE run_id=?", (row["run_id"],)).fetchall()
            result.append({
                **dict(row),
                "failed_step": labels.get(failed[0], failed[0]) if failed else "",
                "models": sorted({u["model"] for u in usage if u["model"]}),
                "routes": sorted({u["route"] for u in usage if u["route"]}),
                "cost": sum((Decimal(str(u["cost_usd"] or 0)) for u in usage), Decimal(0)),
            })
    return result, total


def render_flow(env_id: str) -> str:
    runs, total_cost = _runs_for(env_id)
    name = _flow_name(env_id, runs)
    successful = sum(r["status"] == "done" for r in runs)
    rate = (successful / len(runs) * 100) if runs else 0
    lines = [f"# {name}", "", f"Success rate in the last {len(runs)} runs: {successful} successful ({rate:g}%).",
             f"Total recorded cost across all runs: {_money(total_cost)} USD.", "", "## Last runs", "",
             "| Time (UTC) | Result | Failed step | Models | Routes | Cost |",
             "|---|---|---|---|---|---:|"]
    if not runs:
        lines.append("| No runs recorded | — | — | — | — | $0 |")
    for run in runs:
        lines.append(f"| {_date(run['started_at'])} ({run['run_id']}) | {run['status']} | "
                     f"{run['failed_step'] or '—'} | {', '.join(run['models']) or '—'} | "
                     f"{', '.join(run['routes']) or '—'} | {_money(run['cost'])} |")
    return "\n".join(lines) + "\n"


def write_all() -> list[str]:
    with sqlite3.connect(_db_path()) as db:
        env_ids = [row[0] for row in db.execute("SELECT DISTINCT env_id FROM glacier_runs ORDER BY env_id")]
    # Include saved flows that have not run yet; their notes report no recorded activity.
    for path in vault.list_notes(".json", "environments"):
        try:
            env_ids.append(json.loads(vault.read_note(path))["id"])
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    written = []
    for env_id in sorted(set(env_ids)):
        path = f"status/{env_id}.md"
        body = render_flow(env_id)
        try:
            unchanged = vault.read_note(path) == body
        except (FileNotFoundError, ValueError, IsADirectoryError):
            unchanged = False
        if not unchanged:
            vault.write_note(path, body, agent=AUTHOR)
            written.append(path)
    return written
