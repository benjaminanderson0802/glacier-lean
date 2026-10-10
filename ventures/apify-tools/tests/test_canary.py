from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import daily_canary  # noqa: E402


class CanaryStateTests(unittest.TestCase):
    def test_mismatch_marks_venture_for_maintenance_and_preserves_repair_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_path = Path(temp) / "canary-status.json"
            state_path.write_text(json.dumps({"repair_attempts": 1}), encoding="utf-8")
            with patch.object(
                daily_canary,
                "lookup",
                return_value={"outcome": "unverifiable", "license_number": "failed"},
            ):
                report = daily_canary.run(state_path)
            self.assertEqual(report["status"], "maintenance")
            self.assertEqual(report["repair_attempts"], 1)
            self.assertEqual(report["consecutive_failed_runs"], 1)
            self.assertEqual(len(report["failed_license_numbers"]), 3)


if __name__ == "__main__":
    unittest.main()
