"""Daily source refresh; format changes are surfaced for reviewed release."""

from __future__ import annotations

import json

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
            "row_count": len(result.get("rows", [])),
        }
    changed = [source for source, result in summary.items() if result["changed"] or result["alerts"]]
    print(json.dumps({"sources": summary, "review_required_before_release": changed}, ensure_ascii=False))
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
