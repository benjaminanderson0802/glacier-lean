"""Daily source refresh; format changes are surfaced for reviewed release."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cpsc_prep import load_blocks


def main() -> int:
    _, _, feeds = load_blocks()
    sources = ("cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template")
    summary = {}
    for source_id in sources:
        result = feeds.sync(source_id)
        summary[source_id] = {
            "changed": bool(result.get("changed")),
            "alerts": result.get("alerts", []),
            "row_count": int(result.get("rows", 0)),
        }
    changed = [source for source, result in summary.items() if result["changed"] or result["alerts"]]
    print(json.dumps({"sources": summary, "review_required_before_release": changed}, ensure_ascii=False))
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
