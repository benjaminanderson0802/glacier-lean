from __future__ import annotations

import csv
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify import (  # noqa: E402
    ALLOWED_FILE_HOSTS,
    SourceUnavailable,
    actor_queries,
    load_roster,
    lookup_many,
    read_roster_file,
)


class AlabamaRosterTests(unittest.TestCase):
    def test_manifest_is_valid_and_secrets_needed_is_a_list_of_strings(self) -> None:
        from jsonschema import Draft202012Validator

        schema_path = ROOT.parent / "venture.schema.json"
        manifest = json.loads((ROOT / "venture.json").read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=None).validate(manifest)
        self.assertTrue(all(isinstance(item, str) for item in manifest["secrets_needed"]))

    def test_apify_input_schema_uses_fileupload_and_json_batch_without_nested_schemas(self) -> None:
        schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("editor", schema)
        self.assertEqual(schema["properties"]["roster_file"]["editor"], "fileupload")
        self.assertEqual(schema["properties"]["queries"]["type"], "array")
        self.assertEqual(schema["properties"]["queries"]["editor"], "json")
        self.assertNotIn("items", schema["properties"]["queries"])

    def test_fixture_shaped_like_board_result_loads_literal_fields(self) -> None:
        records = load_roster(ROOT / "tests" / "fixtures" / "alabama_roster.csv")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["license_number"], "AL-EXAMPLE-1042")
        self.assertEqual(records[0]["status"], "Active")
        self.assertEqual(records[0]["expiration_date"], "2027-12-31")
        self.assertEqual(records[0]["business_name"], "Example Building Services LLC")

    def test_exact_license_match_preserves_source_values_and_dates_result(self) -> None:
        roster = load_roster(ROOT / "tests" / "fixtures" / "alabama_roster.csv")
        result = lookup_many(
            roster=roster,
            queries=[{"license_number": "AL-EXAMPLE-1042"}],
            roster_as_of="2026-10-01",
            source_url="https://board.example.gov/roster.csv",
            checked_at="2026-10-10T12:00:00+00:00",
        )[0]
        self.assertEqual(result["outcome"], "match")
        self.assertEqual(result["verification_state"], "verified")
        self.assertEqual(result["status"], "Active")
        self.assertEqual(result["expiration_date"], "2027-12-31")
        self.assertEqual(result["source_url"], "https://board.example.gov/roster.csv")
        self.assertEqual(result["source_as_of"], "2026-10-01")
        self.assertIn("snapshot", result["limitations"])

    def test_exact_business_name_match_only_and_no_match_is_dated(self) -> None:
        roster = load_roster(ROOT / "tests" / "fixtures" / "alabama_roster.csv")
        match = lookup_many(
            roster=roster, queries=[{"name": "Example Building Services LLC"}],
            roster_as_of="2026-10-01", source_url="https://board.example.gov/roster.csv",
        )[0]
        no_match = lookup_many(
            roster=roster, queries=[{"license_number": "AL-UNKNOWN-9999"}],
            roster_as_of="2026-10-01", source_url="https://board.example.gov/roster.csv",
            checked_at="2026-10-10T12:00:00+00:00",
        )[0]
        self.assertEqual(match["outcome"], "match")
        self.assertEqual(no_match["verification_state"], "verified")
        self.assertEqual(no_match["outcome"], "no match found in supplied Alabama roster as of 2026-10-01")

    def test_stale_roster_returns_uncertain_even_when_it_contains_a_match(self) -> None:
        roster = load_roster(ROOT / "tests" / "fixtures" / "alabama_roster.csv")
        stale_date = (date.today() - timedelta(days=366)).isoformat()
        result = lookup_many(
            roster=roster, queries=[{"license_number": "AL-EXAMPLE-1042"}],
            roster_as_of=stale_date, source_url="https://board.example.gov/roster.csv",
        )[0]
        self.assertEqual(result["outcome"], "uncertain — please check")
        self.assertEqual(result["verification_state"], "unverifiable")

    def test_unsupported_columns_and_invalid_queries_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            load_roster_text("Company,City\nExample LLC,Troy\n")
        roster = load_roster(ROOT / "tests" / "fixtures" / "alabama_roster.csv")
        for query in ({}, {"license_number": "1", "name": "Example"}, {"name": "Ex"}):
            with self.assertRaises(ValueError):
                lookup_many(roster=roster, queries=[query], roster_as_of="2026-10-01", source_url="https://board.example.gov/roster.csv")

    def test_file_loader_only_reads_user_supplied_apify_or_local_file_and_enforces_size(self) -> None:
        self.assertIn("api.apify.com", ALLOWED_FILE_HOSTS)
        with self.assertRaises(ValueError):
            read_roster_file("https://genconbd.alabama.gov/roster.csv")
        with self.assertRaises(ValueError):
            read_roster_file("http://api.apify.com/file.csv")
        with patch("scripts.verify.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b"license,name,status,expiration_date\n1,Example,Active,2027-12-31\n"
            content = read_roster_file("https://api.apify.com/v2/key-value-stores/example/records/roster.csv")
            self.assertIn("Example", content)

    def test_batch_input_is_bounded(self) -> None:
        self.assertEqual(len(actor_queries({"queries": [{"license_number": "1"}]})), 1)
        with self.assertRaises(ValueError):
            actor_queries({"queries": []})
        with self.assertRaises(ValueError):
            actor_queries({"queries": [{} for _ in range(101)]})


def load_roster_text(csv_text: str):
    from scripts.verify import load_roster_text as parse

    return parse(csv_text)


if __name__ == "__main__":
    unittest.main()
