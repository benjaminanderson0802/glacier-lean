"""Aggregate per-step usage for the costs screen."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

import store

router = APIRouter()


@router.get("/api/costs")
def costs(env_id: str | None = None, days: int = Query(30, ge=1)):
    """Return usage grouped by serving route and model over the requested period."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    filters = ["r.started_at >= ?"]
    args = [cutoff]
    if env_id:
        filters.append("r.env_id = ?")
        args.append(env_id)
    where = " AND ".join(filters)
    # Keep run ids in the source rows so a run with multiple steps is counted once per group.
    with store._conn() as conn:
        run_rows = conn.execute(
            """SELECT r.run_id, u.route, u.model, u.tokens_in, u.tokens_out, u.cost_usd
               FROM glacier_usage u JOIN glacier_runs r ON r.run_id = u.run_id
               WHERE """ + where,
            args,
        ).fetchall()

    def summarize(key_index, key_name):
        grouped = {}
        for run_id, route, model, tokens_in, tokens_out, cost_usd in run_rows:
            key = (route if key_index == 1 else model) or "unknown"
            item = grouped.setdefault(key, {"_runs": set(), "runs": 0, "steps": 0, "tokens_in": 0,
                                            "tokens_out": 0, "cost_usd": 0.0})
            item["_runs"].add(run_id)
            item["steps"] += 1
            item["tokens_in"] += int(tokens_in or 0)
            item["tokens_out"] += int(tokens_out or 0)
            item["cost_usd"] += float(cost_usd or 0.0)
        return [{key_name: key, **{k: v for k, v in item.items() if k != "_runs"}, "runs": len(item["_runs"])}
                for key, item in sorted(grouped.items())]

    total = sum(float(row[5] or 0.0) for row in run_rows)
    local_steps = sum(1 for row in run_rows if (row[1] or "").startswith("local/"))
    return {
        "total_usd": total,
        "by_route": summarize(1, "route"),
        "by_model": summarize(2, "model"),
        "local_share": local_steps / len(run_rows) if run_rows else 0.0,
        "paid_cap_usd": float(os.environ.get("GLACIER_PAID_CAP_USD", "0") or 0),
    }
