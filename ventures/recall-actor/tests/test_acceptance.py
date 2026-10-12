from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class InputSchemaAcceptanceTests(unittest.TestCase):
    def test_apify_input_schema_has_valid_top_level_and_batch_editor(self) -> None:
        schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(schema),
            {"title", "description", "type", "schemaVersion", "properties", "required"},
        )
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["schemaVersion"], 1)
        self.assertNotIn("editor", schema)
        self.assertEqual(schema["properties"]["queries"]["type"], "array")
        self.assertEqual(schema["properties"]["queries"]["editor"], "json")

    def test_input_accepts_single_item_and_limits_batches_to_100(self) -> None:
        from src.inputs import normalize_input

        self.assertEqual(normalize_input({"barcode": "012345678905"}), [{"barcode": "012345678905"}])
        self.assertEqual(len(normalize_input({"queries": [{"brand": "Example"}] * 100})), 100)
        with self.assertRaises(ValueError):
            normalize_input({"queries": [{"brand": "Example"}] * 101})
        with self.assertRaises(ValueError):
            normalize_input({"queries": []})


class SourceFixtureAcceptanceTests(unittest.TestCase):
    def test_each_source_adapter_parses_its_recorded_official_shape(self) -> None:
        from src.sources import normalize_cpsc, normalize_fda, normalize_nhtsa

        fixture = lambda name: json.loads((ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8"))
        self.assertEqual(normalize_cpsc(fixture("cpsc.json"))[0]["recall_id"], "24-123")
        self.assertEqual(normalize_nhtsa(fixture("nhtsa.json"))[0]["recall_id"], "24V123000")
        for kind in ("food", "drug", "device"):
            with self.subTest(kind=kind):
                self.assertTrue(normalize_fda(fixture(f"fda_{kind}.json"), kind)[0]["recall_id"])


class MatchingAcceptanceTests(unittest.TestCase):
    def test_exact_upc_precedes_conservative_brand_model(self) -> None:
        from src.matching import classify_matches

        recall = {"source": "CPSC", "recall_id": "24-123", "title": "Example heater", "barcode_values": ["012345678905"], "brand": "Example Co", "model": "H-100"}
        outcome, matches = classify_matches({"barcode": "012345678905", "brand": "Unrelated", "model": "X"}, [recall])
        self.assertEqual(outcome, "match")
        self.assertEqual(matches, [recall])

    def test_normalized_brand_and_model_match_and_ambiguous_details_are_uncertain(self) -> None:
        from src.matching import classify_matches

        recall = {"source": "CPSC", "recall_id": "24-123", "title": "Example heater", "barcode_values": [], "brand": "Example Co.", "model": "H-100"}
        self.assertEqual(classify_matches({"brand": "example", "model": "h100"}, [recall])[0], "match")
        self.assertEqual(classify_matches({"brand": "Example"}, [recall])[0], "uncertain")


class ResultAndChargingAcceptanceTests(unittest.TestCase):
    def test_any_source_error_makes_result_uncertain(self) -> None:
        from src.checker import build_result

        result = build_result({"product_name": "Widget"}, [], {"CPSC": {"status": "error", "error": "offline"}})
        self.assertEqual(result["outcome"], "uncertain")
        self.assertEqual(result["matches"], [])
        self.assertIn("CPSC", result["sources_checked"])

    def test_completed_query_is_charged_once_but_outage_only_is_not(self) -> None:
        from src.actor_template import run_actor_queries

        class FakeActor:
            def __init__(self):
                self.rows = []
                self.charges = []
            async def push_data(self, row): self.rows.append(row)
            async def charge(self, **kwargs): self.charges.append(kwargs)
            async def set_status_message(self, message, *, is_terminal): self.message = message

        actor = FakeActor()
        completed = {"outcome": "no_match", "sources_checked": {"CPSC": {"status": "ok"}}}
        outage = {"outcome": "uncertain", "sources_checked": {"CPSC": {"status": "error"}, "FDA": {"status": "error"}}}
        with patch.dict("os.environ", {"ACTOR_TEST_PAY_PER_EVENT": "true", "APIFY_ACTOR_RUN_ID": "test-run"}):
            import asyncio
            asyncio.run(run_actor_queries(actor, [{"id": 1}, {"id": 2}], check_one=lambda q: completed if q["id"] == 1 else outage))
        self.assertEqual(len(actor.rows), 2)
        self.assertEqual(len(actor.charges), 1)
        self.assertEqual(actor.charges[0]["event_name"], "recall-check")


if __name__ == "__main__":
    unittest.main()
