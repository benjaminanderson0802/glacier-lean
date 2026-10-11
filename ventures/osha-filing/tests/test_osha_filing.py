from __future__ import annotations

import json
import importlib.util
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


class OshaFilingAcceptanceTests(unittest.TestCase):
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
        rows = [
            {"establishment_id": "1", "establishment_name": "Large Shop", "industry_code": "332710", "employee_count": 250, "address": "1 Main St", "city": "Town", "state": "IL"},
            {"establishment_id": "2", "establishment_name": "Small Shop", "industry_code": "332710", "employee_count": 19, "address": "2 Main St", "city": "Town", "state": "IL"},
            {"establishment_id": "3", "establishment_name": "Unknown Shop", "industry_code": "000000", "employee_count": 45, "address": "3 Main St", "city": "Town", "state": "IL"},
            {"establishment_id": "4", "establishment_name": "High Hazard Shop", "industry_code": "332710", "employee_count": 45, "address": "4 Main St", "city": "Town", "state": "IL"},
        ]
        with patch.object(OSHA.feeds, "query", return_value=rows):
            result = eligible_prospects(as_of=date(2027, 1, 3))
        self.assertEqual([row["establishment_id"] for row in result["prospects"]], ["1", "4"])
        self.assertEqual(result["result"], "match")
        self.assertIn("uncertain", result["excluded"][0]["result"])

    def test_flows_gate_outreach_and_keep_customer_submission_explicit(self) -> None:
        root = Path(__file__).parents[1]
        outreach = json.loads((root / "flows" / "january-outreach.json").read_text())
        filing = json.loads((root / "flows" / "prepare-300a.json").read_text())
        approval_nodes = [node for node in outreach["nodes"] if node["type"] == "approval"]
        self.assertTrue(approval_nodes)
        self.assertTrue(any("postcard" in node["config"]["prompt"].lower() for node in approval_nodes))
        command_nodes = [node for node in filing["nodes"] if node["type"] == "command"]
        self.assertTrue(command_nodes)
        script = " ".join(node["config"]["cmd"] for node in command_nodes)
        self.assertNotIn("submit", script.lower())


if __name__ == "__main__":
    unittest.main()
