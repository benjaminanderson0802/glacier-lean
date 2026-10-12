"""Per-item recall checking and stable output vocabulary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from .matching import classify_matches
from .sources import check_sources


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def public_match(record: Mapping[str, Any]) -> dict[str, str]:
    return {field: str(record.get(field) or "") for field in ("source", "recall_id", "title", "date", "hazard", "remedy", "url")}


def build_result(query: Mapping[str, Any], recalls: Sequence[Mapping[str, Any]], sources_checked: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    match_outcome, candidates = classify_matches(query, recalls)
    has_source_error = any(source.get("status") == "error" for source in sources_checked.values())
    if has_source_error:
        outcome = "uncertain"
        failed = [name for name, source in sources_checked.items() if source.get("status") == "error"]
        message = f"uncertain — please check ({', '.join(failed)} unavailable)"
    elif match_outcome == "match":
        outcome = "match"
        message = "match"
    elif match_outcome == "uncertain":
        outcome = "uncertain"
        message = "uncertain — please check"
    else:
        outcome = "no_match"
        checked_sources = [name for name, source in sources_checked.items() if source.get("status") == "ok"]
        date = _now()[:10]
        source_names = ", ".join(checked_sources)
        message = f"no match found in {source_names} as of {date}"
    return {
        "outcome": outcome,
        "message": message,
        "query": dict(query),
        "matches": [public_match(record) for record in candidates],
        "sources_checked": {name: dict(status) for name, status in sources_checked.items()},
        "checked_at": _now(),
    }


def check_one(query: Mapping[str, Any]) -> dict[str, Any]:
    recalls, statuses = check_sources(query)
    return build_result(query, recalls, statuses)
