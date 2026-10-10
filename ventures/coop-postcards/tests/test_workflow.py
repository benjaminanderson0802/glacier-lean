"""Acceptance checks for co-op claim preparation and street-card safeguards."""
from datetime import date
import unittest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow import (
    check_claim,
    claim_reminder_dates,
    check_route_card,
    render_postcard,
)


class CoOpWorkflowAcceptanceTests(unittest.TestCase):
    def test_claim_requires_preapproval_and_shared_rules_pass_before_filing(self):
        rules = {
            "program_year": "2026",
            "expires_on": "2026-12-31",
            "required_evidence": ["ad_proof", "invoice"],
            "requires_preapproval": True,
        }
        fields = {
            "program_year": "2026",
            "ad_proof": "proof.pdf",
            "invoice": "invoice.pdf",
            "preapproval_id": "APPROVED-7",
            "dealer_authorized": True,
        }
        # This workspace has no shared rules block yet, so a complete intake stays uncertain.
        self.assertEqual(check_claim(fields, rules)["verdict"], "uncertain")
        self.assertFalse(check_claim(fields, rules)["filing_ready"])
        fields.pop("preapproval_id")
        self.assertEqual(check_claim(fields, rules)["verdict"], "fail")
        self.assertEqual(check_claim({**fields, "preapproval_id": "", "dealer_authorized": True}, rules)["verdict"], "fail")

    def test_missing_rules_or_evidence_is_uncertain_and_not_filing_ready(self):
        result = check_claim({"dealer_authorized": True}, {})
        self.assertEqual(result["verdict"], "uncertain")
        self.assertFalse(result["filing_ready"])

    def test_claim_reminders_fall_60_and_30_days_before_expiry(self):
        self.assertEqual(
            claim_reminder_dates("2026-12-31"),
            [date(2026, 11, 1), date(2026, 12, 1)],
        )

    def test_route_card_rejects_duplicate_categories_or_unapproved_ads(self):
        card = {
            "campaign_id": "campaign-1",
            "town": "Sampleville",
            "route_id": "R-01",
            "fill_by": "2026-11-15",
            "buyers": [
                {"category": "HVAC", "written_approval": True},
                {"category": "HVAC", "written_approval": True},
            ],
            "street_jobs": [{"address": "10 Main St", "homeowner_name": "should not be used"}],
        }
        result = check_route_card(card)
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("duplicate category", " ".join(result["issues"]))
        self.assertIn("homeowner name", " ".join(result["issues"]))

    def test_route_card_must_be_timed_for_november_dealer_budgets(self):
        result = check_route_card({
            "campaign_id": "campaign-2",
            "town": "Sampleville", "route_id": "R-02", "fill_by": "2026-10-31",
            "from": {"name": "Glacier Co-op & Street Cards"},
            "to": {"address_line1": "1 Business Way"}, "buyers": [], "street_jobs": [],
        })
        self.assertIn("year-end dealer card fill-by date must be in November", result["issues"])

    def test_flows_gate_each_submission_and_mail_send(self):
        folder = Path(__file__).resolve().parents[1] / "flows"
        for flow_name, action in (("coop-claim-readiness", "run_approved_claim.py"), ("street-postcard-proof", "send_postcard.py")):
            flow = json.loads((folder / f"{flow_name}.json").read_text(encoding="utf-8"))
            nodes = flow["nodes"]
            approval_index = next(i for i, node in enumerate(nodes) if node["type"] == "approval")
            command_index = next(i for i, node in enumerate(nodes) if action in node.get("config", {}).get("cmd", ""))
            self.assertLess(approval_index, command_index)
            self.assertIn("--approval {run}", nodes[command_index]["config"]["cmd"])

    def test_card_rendering_uses_real_data_and_clear_sender_without_homeowner_name(self):
        record = {"dealer_name": "Northside Heating", "town": "Sampleville", "street": "10 Main St"}
        front, back = render_postcard(record)
        self.assertIn("Northside Heating", front + back)
        self.assertIn("10 Main St", front + back)
        self.assertNotIn("government notice", (front + back).lower())


if __name__ == "__main__":
    unittest.main()
