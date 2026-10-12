"""Daily source refresh; format changes are surfaced for reviewed release."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cpsc_prep import load_blocks, source_revision


def main() -> int:
    _, _, feeds = load_blocks()
    sources = ("cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template")
    summary = {}
    for source_id in sources:
        result = feeds.sync(source_id)
        query = getattr(feeds, "query", None)
        rows = query(source_id) if callable(query) else []
        source_urls = sorted({str(row.get("source_url")) for row in rows if row.get("source_url")})
        fetched_at = sorted({str(row.get("fetched_at")) for row in rows if row.get("fetched_at")})
        summary[source_id] = {
            "changed": bool(result.get("changed")),
            "alerts": result.get("alerts", []),
            "row_count": int(result.get("rows", 0)),
            "status": result.get("status", "unknown"),
            "local_revision": source_revision(source_id, rows),
            "source_url": source_urls[0] if source_urls else None,
            "fetched_at": fetched_at[-1] if fetched_at else None,
        }
    changed = [source for source, result in summary.items() if result["changed"] or result["alerts"]]
    print(json.dumps({"sources": summary, "review_required_before_release": changed}, ensure_ascii=False))
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
