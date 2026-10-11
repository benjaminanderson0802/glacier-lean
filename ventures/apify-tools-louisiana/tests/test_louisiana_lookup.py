from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lookup import RateLimiter, SourceUnavailable, lookup_many  # noqa: E402


class LookupContractTests(unittest.TestCase):
    def test_apify_input_schema_uses_json_editor_for_batches_without_nested_schemas(self) -> None:
        schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("editor", schema)
        self.assertEqual(schema["properties"]["queries"]["type"], "array")
        self.assertEqual(schema["properties"]["queries"]["editor"], "json")
        self.assertNotIn("items", schema["properties"]["queries"])

    def test_query_search_posts_to_official_keyless_search_and_returns_license_record(self) -> None:
        search = """<table id="AccountSearchTable"><tbody><tr>
          <td><a onclick="ShowAccountDetails('opaque%3d%3d', );">09 Construction Services, LLC</a></td>
          <td>Bossier City</td><td>LA</td></tr></tbody></table>"""
        detail = """<fieldset><legend>Licenses</legend>
          <div class="display-label">License</div><div class="display-field">CL.68755</div>
          <div class="display-label">Type</div><div class="display-field">Commercial License Certificate</div>
          <div class="display-label">Status</div><div class="display-field"><span>Active</span></div>
          <div class="display-label">Expiration Date</div><div class="display-field">07/18/2029</div>
          </fieldset>"""
        with patch("src.lookup._read_url", side_effect=[search, detail]) as read:
            result = lookup_many(license_number="CL.68755")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["business_name"], "09 Construction Services, LLC")
        self.assertEqual(result[0]["license_number"], "CL.68755")
        self.assertEqual(result[0]["status"], "Active")
        self.assertEqual(result[0]["expiration_date"], "2029-07-18")
        self.assertTrue(result[0]["source_url"].startswith(
            "https://arlspublic.lslbc.louisiana.gov/Public/_DisplayOnlineDetails/?key="
        ))
        self.assertEqual(read.call_count, 2)
        self.assertIn("AccountNumber=68755", read.call_args_list[0].kwargs["data"].decode())

    def test_name_lookup_filters_returned_records_and_respects_limit(self) -> None:
        search = """<table id="AccountSearchTable"><tr>
          <td><a onclick="ShowAccountDetails('first%3d%3d', );">09 Construction Services, LLC</a></td>
          <td>Bossier City</td><td>LA</td></tr>
          <tr><td><a onclick="ShowAccountDetails('second%3d%3d', );">Another Construction, LLC</a></td>
          <td>Town</td><td>LA</td></tr></table>"""
        detail = """<div class="display-label">License</div><div class="display-field">CL.68755</div>
          <div class="display-label">Type</div><div class="display-field">Commercial License Certificate</div>
          <div class="display-label">Status</div><div class="display-field">Active</div>
          <div class="display-label">Expiration Date</div><div class="display-field">07/18/2029</div>"""
        with patch("src.lookup._read_url", side_effect=[search, detail]):
            result = lookup_many(name="09 Construction", max_results=1)
        self.assertEqual([row["business_name"] for row in result], ["09 Construction Services, LLC"])

    def test_incomplete_license_detail_is_uncertain_not_a_match(self) -> None:
        search = """<table id="AccountSearchTable"><tbody><tr>
          <td><a onclick="ShowAccountDetails('opaque%3d%3d', );">09 Construction Services, LLC</a></td>
          <td>Bossier City</td><td>LA</td></tr></tbody></table>"""
        detail = """<div class="display-label">License</div><div class="display-field">CL.68755</div>
          <div class="display-label">Type</div><div class="display-field">Commercial License Certificate</div>
          <div class="display-label">Status</div><div class="display-field">Active</div>"""
        with patch("src.lookup._read_url", side_effect=[search, detail]):
            result = lookup_many(license_number="CL.68755")
        self.assertEqual(result[0]["outcome"], "uncertain — please check")
        self.assertEqual(result[0]["verification_state"], "uncertain")

    def test_readable_no_match_is_dated_and_source_failure_is_unverifiable(self) -> None:
        with patch("src.lookup._read_url", return_value="No results found for search criteria."):
            no_match = lookup_many(license_number="999999")
        self.assertEqual(no_match[0]["verification_state"], "verified")
        self.assertIn("no match found", no_match[0]["outcome"])
        self.assertTrue(no_match[0]["checked_at"].endswith("+00:00"))

        with patch("src.lookup._read_url", side_effect=SourceUnavailable("offline")):
            unavailable = lookup_many(license_number="68755")
        self.assertEqual(unavailable[0]["outcome"], "uncertain — please check")
        self.assertEqual(unavailable[0]["verification_state"], "unverifiable")

        malformed = '<table id="AccountSearchTable"><tr><td>changed markup</td></tr></table>'
        with patch("src.lookup._read_url", return_value=malformed):
            changed_schema = lookup_many(license_number="999999")
        self.assertEqual(changed_schema[0]["outcome"], "uncertain — please check")
        self.assertEqual(changed_schema[0]["verification_state"], "unverifiable")

    def test_query_validation_and_request_spacing(self) -> None:
        with self.assertRaises(ValueError):
            lookup_many()
        with self.assertRaises(ValueError):
            lookup_many(name="AB")
        limiter = RateLimiter(1.0)
        with patch("src.lookup.time.monotonic", side_effect=[10.0, 10.2]), patch(
            "src.lookup.time.sleep"
        ) as sleep:
            limiter.wait()
            limiter.wait()
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.8)


if __name__ == "__main__":
    unittest.main()
