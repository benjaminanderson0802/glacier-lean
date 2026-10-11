from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import daily_canary  # noqa: E402


class LouisianaCanaryTests(unittest.TestCase):
    def test_matching_canaries_produce_healthy_state(self) -> None:
        expected = daily_canary.CANARIES
        with tempfile.TemporaryDirectory() as temp, patch.object(
            daily_canary,
            "lookup_many",
            side_effect=[[{
                "outcome": "match",
                **{key: row[key] for key in ("license_number", "business_name", "status", "expiration_date")},
            }] for row in expected],
        ):
            report = daily_canary.run(Path(temp) / "state.json")
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["failed_license_numbers"], [])
        self.assertEqual(len(report["results"]), 3)

    def test_changed_live_record_enters_maintenance_without_repairing_itself(self) -> None:
        wrong = {"outcome": "uncertain — please check", "verification_state": "unverifiable"}
        with tempfile.TemporaryDirectory() as temp, patch.object(
            daily_canary, "lookup_many", return_value=[wrong]
        ):
            report = daily_canary.run(Path(temp) / "state.json")
        self.assertEqual(report["status"], "maintenance")
        self.assertEqual(len(report["failed_license_numbers"]), 3)
        self.assertEqual(report["repair_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
