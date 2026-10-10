#!/usr/bin/env python3
"""Compare three recorded license canaries with Mississippi's public contractor lookup."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lookup import lookup  # noqa: E402

CANARIES = json.loads((ROOT / "tests" / "canaries.json").read_text(encoding="utf-8"))


def run(state_path: Path) -> dict[str, object]:
    expected_fields = ("license_number", "business_name", "status", "expiration_date")
    results = []
    failures = []
    for canary in CANARIES:
        actual = lookup(license_number=canary["license_number"])
        ok = actual.get("outcome") == "match" and all(
            actual.get(field) == canary[field] for field in expected_fields
        )
        results.append({"license_number": canary["license_number"], "ok": ok, "actual": actual})
        if not ok:
            failures.append(canary["license_number"])

    previous: dict[str, object] = {}
    if state_path.exists():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {"status": "maintenance", "reason": "Previous canary state was unreadable"}
    if failures:
        status = "maintenance"
        failure_count = int(previous.get("consecutive_failed_runs", 0)) + 1
        reason = "Canary data changed or could not be verified; review before returning the Store Actor to service."
    else:
        status = "healthy"
        failure_count = 0
        reason = "All three Mississippi contractor canaries matched the recorded board values."

    report = {
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "consecutive_failed_runs": failure_count,
        "repair_attempts": int(previous.get("repair_attempts", 0)),
        "retire_after_repair_attempts": 2,
        "reason": reason,
        "failed_license_numbers": failures,
        "results": results,
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    state_root = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    state_path = state_root / "ventures" / "apify-tools" / "canary-status.json"
    report = run(state_path)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
