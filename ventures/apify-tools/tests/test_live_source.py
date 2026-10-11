"""Release checks against Mississippi's public contractor lookup."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lookup import RateLimiter, SourceUnavailable, lookup  # noqa: E402


CANARIES = json.loads((ROOT / "tests" / "canaries.json").read_text())


class LiveMississippiSourceTests(unittest.TestCase):
    def test_three_recorded_license_canaries_match_live_board_data(self) -> None:
        for canary in CANARIES:
            with self.subTest(license_number=canary["license_number"]):
                result = lookup(license_number=canary["license_number"])
                self.assertEqual(result["outcome"], "match")
                self.assertEqual(result["license_number"], canary["license_number"])
                self.assertEqual(result["business_name"], canary["business_name"])
                self.assertEqual(result["status"], canary["status"])
                self.assertEqual(result["expiration_date"], canary["expiration_date"])
                self.assertEqual(result["source_url"], result["source_url"].strip())
                self.assertTrue(result["source_url"].startswith("https://search.msboc.us/"))
                checked_at = datetime.fromisoformat(result["checked_at"])
                self.assertEqual(checked_at.utcoffset(), timezone.utc.utcoffset(checked_at))

    def test_live_name_search_returns_source_backed_record(self) -> None:
        result = lookup(name="3H")
        self.assertEqual(result["outcome"], "match")
        self.assertIn("3H CONSTRUCTION", result["business_name"])
        self.assertTrue(result["license_number"])
        self.assertTrue(result["expiration_date"])
        self.assertTrue(result["source_url"].startswith("https://search.msboc.us/"))


class LookupSafetyTests(unittest.TestCase):
    def test_rate_limiter_waits_between_board_requests(self) -> None:
        limiter = RateLimiter(interval_seconds=1.0)
        with patch("src.lookup.time.monotonic", side_effect=[10.0, 10.2]), patch(
            "src.lookup.time.sleep"
        ) as sleep:
            limiter.wait()
            limiter.wait()
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.8)

    def test_exactly_one_search_key_is_required(self) -> None:
        with self.assertRaises(ValueError):
            lookup()
        with self.assertRaises(ValueError):
            lookup(license_number="22649", name="another query")

    def test_readable_empty_search_is_dated_and_verified(self) -> None:
        with patch("src.lookup._search", return_value=[]):
            result = lookup(license_number="999999999")
        self.assertTrue(result["outcome"].startswith("no match found in Mississippi"))
        self.assertEqual(result["verification_state"], "verified")
        self.assertEqual(result["status"], None)

    def test_unavailable_source_is_uncertain_and_never_reported_as_no_match(self) -> None:
        with patch("src.lookup._search", side_effect=SourceUnavailable("offline")):
            result = lookup(license_number="22649")
        self.assertEqual(result["outcome"], "uncertain — please check")
        self.assertEqual(result["verification_state"], "unverifiable")
        self.assertIn("source_url", result)
        self.assertNotIn("no match found", result["outcome"])


if __name__ == "__main__":
    unittest.main()
