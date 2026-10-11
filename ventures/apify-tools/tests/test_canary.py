from __future__ import annotations

import json
import asyncio
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

    def test_publication_gate_requires_three_distinct_owner_approvals_and_review(self) -> None:
        root = Path(__file__).resolve().parents[1]
        flow = json.loads((root / "flows" / "your-step-publish.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
        prompt = flow["nodes"][0]["config"]["prompt"].casefold()
        self.assertIn("first three distinct actor publications", prompt)
        self.assertIn("run this approval separately", prompt)
        self.assertIn("different engine review", prompt)
        self.assertIn("never reuse an earlier approval", prompt)
        self.assertIn("first three distinct actor publications", manifest["your_steps"][2]["detail"].casefold())

    def test_reusable_actor_template_publishes_records_and_charges_readable_results(self) -> None:
        from src.actor_template import run_lookup_actor

        class FakeActor:
            def __init__(self):
                self.rows = []
                self.charges = []
                self.status = None

            async def push_data(self, row):
                self.rows.append(row)

            async def charge(self, **kwargs):
                self.charges.append(kwargs)

            async def set_status_message(self, message, *, is_terminal):
                self.status = (message, is_terminal)

        actor = FakeActor()
        result = {"verification_state": "verified", "status": "Licensed"}
        with patch.dict("os.environ", {"ACTOR_TEST_PAY_PER_EVENT": "true", "APIFY_ACTOR_RUN_ID": "test-run"}):
            asyncio.run(run_lookup_actor(
                actor,
                [{"license_number": "22649", "name": None, "max_results": 1}],
                lookup_many=lambda **kwargs: [result],
                source_name="Test Board",
                event_name="lookup",
            ))
        self.assertEqual(actor.rows, [result])
        self.assertEqual(len(actor.charges), 1)
        self.assertEqual(actor.charges[0]["event_name"], "lookup")
        self.assertEqual(actor.status, ("Finished 1 lookups against Test Board.", True))

    def test_second_board_is_blocked_until_review_and_owner_approval(self) -> None:
        root = Path(__file__).resolve().parents[1]
        checklist = (root / "BOARD_REVIEW.md").read_text(encoding="utf-8").casefold()
        self.assertIn("do not add or publish a second board", checklist)
        self.assertIn("different-engine code and store-listing review", checklist)
        self.assertIn("separate owner approval", checklist)


if __name__ == "__main__":
    unittest.main()
