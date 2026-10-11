from __future__ import annotations

import json
import importlib.util
import csv
import contextlib
import io
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "osha_filing.py"
SPEC = importlib.util.spec_from_file_location("osha_filing", SCRIPT)
assert SPEC and SPEC.loader
OSHA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OSHA)
build_300a_packet = OSHA.build_300a_packet
eligible_prospects = OSHA.eligible_prospects
validate_300a = OSHA.validate_300a
prepare_ita_local_mock = OSHA.prepare_ita_local_mock
load_customer_csv = OSHA.load_customer_csv


class OshaFilingAcceptanceTests(unittest.TestCase):
    def test_customer_injury_log_csv_builds_review_worksheet(self) -> None:
        root = Path(__file__).parents[1]
        fixture = root / "fixtures" / "injury-log.example.csv"
        fields = load_customer_csv(fixture)
        packet = build_300a_packet(fields)
        self.assertEqual(fields["total_cases"], 2)
        self.assertEqual(fields["cases_with_days_away"], 1)
        self.assertEqual(fields["cases_with_job_transfer_or_restriction"], 1)
        self.assertEqual(fields["days_away"], 3)
        self.assertEqual(fields["job_transfer_or_restriction_days"], 5)
        self.assertEqual(packet["result"], "match")
        self.assertEqual(packet["signature"], "customer_signature_required")
        self.assertEqual(packet["submission"], "customer_submits_in_osha_ita")
        self.assertIn("posts it at the establishment February 1–April 30", packet["html"])
        self.assertIn("submits the required data in OSHA ITA by March 2", packet["html"])

    def test_cli_creates_html_worksheet_from_fixture_csv(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "worksheet.html"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(OSHA.main(["prepare-300a", "--input", str(root / "fixtures" / "injury-log.example.csv"), "--output", str(output)]), 0)
            report = json.loads(stdout.getvalue())
            worksheet = output.read_text(encoding="utf-8")
        self.assertEqual(report["result"], "match")
        self.assertEqual(report["signature"], "customer_signature_required")
        self.assertEqual(report["submission"], "customer_submits_in_osha_ita")
        self.assertIn("Example Metal Works", worksheet)
        self.assertIn("Total cases", worksheet)

    def test_csv_template_has_a_zero_injury_row_and_complete_columns(self) -> None:
        root = Path(__file__).parents[1]
        template = root / "templates" / "customer-injury-log-template.csv"
        fields = load_customer_csv(template)
        self.assertEqual(fields["total_cases"], 0)
        self.assertEqual(fields["year"], "")
        self.assertEqual(fields["total_hours_worked"], "")

    def test_deadlines_include_distinct_submission_and_posting_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            OSHA.schedule_deadlines("est-300a", 2027, "OSHA Form 300A")
            from ventures.blocks.deadlines import due

            filing_open = due(date(2027, 1, 2))
            posting_open = due(date(2027, 2, 1))
            filing_due = due(date(2027, 3, 2))
            posting_close = due(date(2027, 4, 30))
        self.assertEqual(filing_open[0]["milestone"], "window_open")
        self.assertEqual(filing_due[0]["milestone"], "window_close")
        self.assertTrue(any("posting period" in row["label"] for row in posting_open))
        self.assertTrue(any("posting period" in row["label"] for row in posting_close))
        self.assertTrue(all("customer" in str(step).lower() for row in posting_close for step in row["glacier_steps"]))

    def test_300a_totals_and_hours_are_checked_before_packet_creation(self) -> None:
        valid = {
            "establishment_name": "Example Metal Works",
            "establishment_id": "123456789",
            "year": 2025,
            "industry_code": "332710",
            "average_employees": 25,
            "total_hours_worked": 48000,
            "total_deaths": 0,
            "cases_with_days_away": 1,
            "cases_with_job_transfer_or_restriction": 2,
            "other_recordable_cases": 3,
            "total_cases": 6,
            "days_away": 4,
            "job_transfer_or_restriction_days": 7,
            "executive_name": "Jordan Example",
            "executive_title": "Owner",
        }
        self.assertEqual(validate_300a(valid)["verdict"], "pass")
        packet = build_300a_packet(valid)
        self.assertIn("CERTIFICATION", packet["html"].upper())
        self.assertEqual(packet["signature"], "customer_signature_required")
        self.assertEqual(packet["submission"], "customer_submits_in_osha_ita")

        invalid = {**valid, "total_cases": 2, "total_hours_worked": 300000}
        result = validate_300a(invalid)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("total_cases" in item["rule"] for item in result["results"]))

    def test_missing_customer_confirmation_is_uncertain(self) -> None:
        result = validate_300a({"establishment_name": "Example", "year": 2025})
        self.assertEqual(result["verdict"], "uncertain")
        self.assertTrue(all(item.get("cite") for item in result["results"]))

    def test_shared_filer_is_guarded_to_local_mock(self) -> None:
        with self.assertRaisesRegex(ValueError, "local mock"):
            prepare_ita_local_mock({"year": 2025}, {"base_url": "https://ita.osha.gov", "username": "customer", "password": "not-used"})

    def test_january_window_deadline_uses_shared_tracker_and_fires_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            from ventures.blocks.deadlines import add, due

            add("test-establishment", "2027-01-02", "jan2-mar2", "OSHA Form 300A filing")
            self.assertEqual(due(date(2027, 1, 2))[0]["milestone"], "window_open")
            self.assertEqual(due(date(2027, 1, 2)), [])
            self.assertEqual(due(date(2027, 3, 2))[0]["milestone"], "window_close")

    def test_prospect_scoring_uses_public_data_without_classifying_compliance(self) -> None:
        fixture = Path(__file__).parents[1] / "fixtures" / "ita-establishments.example.csv"
        with fixture.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        with patch.object(OSHA.feeds, "query", return_value=rows):
            result = eligible_prospects(as_of=date(2027, 1, 3))
        self.assertEqual([row["establishment_id"] for row in result["prospects"]], ["1", "4"])
        self.assertEqual(result["result"], "match")
        self.assertIn("uncertain", result["excluded"][0]["result"])

    def test_ita_fixture_screen_keeps_missing_or_ambiguous_data_uncertain(self) -> None:
        fixture = Path(__file__).parents[1] / "fixtures" / "ita-establishments.example.csv"
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(OSHA.main(["prospects", "--fixture", str(fixture), "--as-of", "2027-01-03", "--output", str(Path(tmp) / "selected.json")]), 0)
            report = json.loads(stdout.getvalue())
        self.assertEqual(report["source_mode"], "synthetic_fixture")
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["uncertain_count"], 2)

    def test_first_five_public_summary_rows_become_unsigned_review_worksheets(self) -> None:
        rows = [
            {
                "establishment_id": str(index), "establishment_name": f"Sample establishment {index}",
                "street_address": f"{index} Main St", "city": "Atlanta", "state": "GA", "zip_code": "30301",
                "naics_code": "238220", "size": "3", "year_filing_for": "2025",
                "annual_average_employees": "280", "total_hours_worked": "500000",
                "total_deaths": "0", "total_dafw_cases": "1", "total_djtr_cases": "2",
                "total_other_cases": "3", "total_dafw_days": "4", "total_djtr_days": "5",
            }
            for index in range(1, 8)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = OSHA.prepare_first_five(
                records=rows, output_dir=Path(tmp), as_of=date(2026, 10, 11),
                source_url="https://www.osha.gov/itadata",
            )
            self.assertEqual(result["source_canary"]["passed"], True)
            self.assertEqual(result["source_canary"]["establishment_ids_present"], 7)
            self.assertEqual(result["worksheets_prepared"], 5)
            self.assertEqual(result["screening_window_date"], "2027-01-03")
            for item in result["worksheets"]:
                content = Path(item["path"]).read_text()
                self.assertIn("Sample establishment", content)
                self.assertIn("https://www.osha.gov/itadata", content)
                self.assertIn("historical submissions", content)
                self.assertIn("Signature: ____________________________________", content)
                self.assertIn("Glacier does not certify or submit", content)
                self.assertEqual(item["signature"], "customer_signature_required")
                self.assertEqual(item["submission"], "customer_submits_in_osha_ita")
            self.assertEqual(result["mail_status"], "not_sent")
            self.assertFalse(result["submission_by_glacier"])

    def test_first_five_refuses_source_without_unique_establishment_id_canary(self) -> None:
        rows = [
            {"establishment_id": "same", "establishment_name": "Sample", "size": "3"},
            {"establishment_id": "same", "establishment_name": "Sample", "size": "3"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source canary failed"):
                OSHA.prepare_first_five(
                    records=rows, output_dir=Path(tmp), as_of=date(2026, 10, 11),
                    source_url="https://www.osha.gov/itadata",
                )
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_flows_gate_outreach_and_keep_customer_submission_explicit(self) -> None:
        root = Path(__file__).parents[1]
        outreach = json.loads((root / "flows" / "january-outreach.json").read_text())
        filing = json.loads((root / "flows" / "prepare-300a.json").read_text())
        approval_nodes = [node for node in outreach["nodes"] if node["type"] == "approval"]
        self.assertTrue(approval_nodes)
        self.assertTrue(any("postcard" in node["config"]["prompt"].lower() for node in approval_nodes))
        approval_ids = {node["id"] for node in filing["nodes"] if node["type"] == "approval"}
        approval_edges = [edge for edge in filing["edges"] if edge["source"] in approval_ids]
        self.assertTrue(approval_edges)
        self.assertTrue(all(edge.get("label") == "yes" for edge in approval_edges))
        self.assertGreaterEqual(filing["max_steps"], len(filing["nodes"]))
        command_nodes = [node for node in filing["nodes"] if node["type"] == "command"]
        self.assertTrue(command_nodes)
        script = " ".join(node["config"]["cmd"] for node in command_nodes)
        self.assertNotIn("submit", script.lower())


if __name__ == "__main__":
    unittest.main()
