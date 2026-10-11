from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lookup import lookup_many  # noqa: E402


CANARIES = json.loads((ROOT / "tests" / "canaries.json").read_text(encoding="utf-8"))


class LiveLouisianaSourceTests(unittest.TestCase):
    def test_three_recorded_license_canaries_match_live_board_data(self) -> None:
        for canary in CANARIES:
            with self.subTest(license_number=canary["license_number"]):
                result = lookup_many(license_number=canary["license_number"])
                self.assertTrue(result)
                record = result[0]
                self.assertEqual(record["outcome"], "match")
                self.assertEqual(record["license_number"], canary["license_number"])
                self.assertEqual(record["business_name"], canary["business_name"])
                self.assertEqual(record["status"], canary["status"])
                self.assertEqual(record["expiration_date"], canary["expiration_date"])
                self.assertTrue(record["source_url"].startswith(
                    "https://arlspublic.lslbc.louisiana.gov/Public/_DisplayOnlineDetails/"
                ))
                checked_at = datetime.fromisoformat(record["checked_at"])
                self.assertEqual(checked_at.utcoffset(), timezone.utc.utcoffset(checked_at))


if __name__ == "__main__":
    unittest.main()
