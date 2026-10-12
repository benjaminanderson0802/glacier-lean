import csv
import json
import tempfile
import unittest
from pathlib import Path

from ventures.recall_checker import api_match_payload, check_item, generate_pages, match_item, process_csv


class RecallMatcherAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.recall = {
            "source_id": "cpsc_recalls",
            "record_id": "24001",
            "record_date": "2026-09-01",
            "fetched_at": "2026-10-10T00:00:00Z",
            "source_url": "https://www.cpsc.gov/Recalls/2026/Example-Recall",
            "data": {
                "RecallNumber": "24001",
                "RecallDate": "2026-09-01",
                "Title": "Example blender model BL-100",
                "Description": "Example brand blender, model BL-100, UPC 012345678905.",
                "URL": "https://www.cpsc.gov/Recalls/2026/Example-Recall",
                "UPC": "012345678905",
                "Model": "BL-100",
                "Brand": "Example",
            },
        }

    def test_exact_barcode_is_a_match_with_official_citation(self):
        result = match_item({"barcode": "012345678905"}, [self.recall], as_of="2026-10-10")
        self.assertEqual(result["result"], "match")
        self.assertEqual(result["recalls"][0]["recall_number"], "24001")
        self.assertEqual(result["recalls"][0]["official_url"], self.recall["source_url"])

    def test_borderline_similar_model_is_uncertain(self):
        result = match_item({"brand": "Example", "model": "BL-10O"}, [self.recall], as_of="2026-10-10")
        self.assertEqual(result["result"], "uncertain — please check")

    def test_clean_item_uses_required_source_and_date_vocabulary(self):
        result = match_item({"brand": "Unrelated", "model": "SAFE-1"}, [self.recall], as_of="2026-10-10")
        self.assertEqual(result["result"], "no match found in CPSC, NHTSA, FDA and FSIS as of 2026-10-10")

    def test_empty_or_stale_data_never_claims_no_match(self):
        result = match_item({"barcode": "999"}, [], as_of="2026-10-10")
        self.assertEqual(result["result"], "uncertain — please check")

    def test_api_refuses_clean_result_when_any_source_is_missing(self):
        def fake_query(source_id):
            return [self.recall] if source_id == "cpsc_recalls" else []

        result = check_item({"barcode": "998"}, feed_query=fake_query, as_of="2026-10-10")
        self.assertEqual(result["result"], "uncertain — please check")
        self.assertIn("nhtsa_recalls", result["detail"])

    def test_api_rejects_non_object_request(self):
        with self.assertRaises(ValueError):
            api_match_payload([])

    def test_mv3_extension_requests_only_current_tab_and_local_api_access(self):
        manifest = json.loads((Path(__file__).parents[1] / "extension" / "manifest.json").read_text())
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(set(manifest["permissions"]), {"activeTab", "scripting", "storage"})
        self.assertEqual(set(manifest["host_permissions"]), {"http://127.0.0.1:8765/*", "https://api.apify.com/*"})

    def test_hosted_api_token_is_not_persisted_between_popup_sessions(self):
        root = Path(__file__).parents[1]
        script = (root / "extension" / "popup.js").read_text(encoding="utf-8")
        popup = (root / "extension" / "popup.html").read_text(encoding="utf-8")
        policy = (root / "store" / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn('const settingIds = ["check-mode", "actor-id"];', script)
        self.assertIn('chrome.storage.local.get({ "check-mode": "local", "actor-id": "" })', script)
        self.assertIn("token stays in this popup", popup)
        self.assertIn("not saved after the popup closes", policy)

    def test_owner_steps_link_store_secrets_and_require_host_choice(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
        steps = {step["id"]: step for step in manifest["your_steps"]}
        self.assertIn("https://chrome.google.com/webstore/devconsole", steps["launch-setup"]["links"])
        self.assertIn("#/settings/secrets", steps["launch-setup"]["links"])
        self.assertIn("Choose and configure a public host", steps["review-first-pages"]["detail"])

    def test_batch_flow_connects_synthetic_input_approval_to_checker(self):
        flow_path = Path(__file__).parents[1] / "flows" / "recall-batch-check.json"
        flow = json.loads(flow_path.read_text(encoding="utf-8"))
        input_edge = next(edge for edge in flow["edges"] if edge["source"] == "owner_input_ready")
        self.assertEqual((input_edge["target"], input_edge["label"]), ("check_inventory", "yes"))

    def test_first_page_flow_records_incomplete_feed_blocker(self):
        flow_path = Path(__file__).parents[1] / "flows" / "recall-review-first-pages.json"
        flow = json.loads(flow_path.read_text(encoding="utf-8"))
        blocked_edge = next(edge for edge in flow["edges"] if edge["source"] == "pages_ready" and edge["label"] == "no")
        self.assertEqual(blocked_edge["target"], "feed_blocked")
        self.assertIn("do not host any recall pages", next(node for node in flow["nodes"] if node["id"] == "feed_blocked")["config"]["prompt"])

    def test_csv_marks_each_row_and_preserves_original_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            incoming = Path(directory) / "inventory.csv"
            outgoing = Path(directory) / "flagged.csv"
            incoming.write_text("sku,barcode\nA,012345678905\nB,999\n", encoding="utf-8")
            process_csv(incoming, outgoing, [self.recall], as_of="2026-10-10")
            with outgoing.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual([row["recall_result"] for row in rows], ["match", "no match found in CPSC, NHTSA, FDA and FSIS as of 2026-10-10"])
        self.assertEqual(rows[0]["sku"], "A")

    def test_csv_returns_uncertain_when_a_required_feed_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            incoming = Path(directory) / "inventory.csv"
            outgoing = Path(directory) / "flagged.csv"
            incoming.write_text("brand,model\nUnrelated,SAFE-1\n", encoding="utf-8")
            process_csv(incoming, outgoing, [self.recall], as_of="2026-10-10", missing_sources=["fsis_recalls"])
            with outgoing.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["recall_result"], "uncertain — please check")
        self.assertEqual(rows[0]["official_links"], "")

    def test_csv_returns_uncertain_when_one_source_snapshot_is_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            incoming = Path(directory) / "inventory.csv"
            outgoing = Path(directory) / "flagged.csv"
            incoming.write_text("brand,model\nUnrelated,SAFE-1\n", encoding="utf-8")
            rows = [
                {"source_id": "cpsc_recalls", "fetched_at": "2020-01-01T00:00:00Z", "data": {}},
                {"source_id": "nhtsa_recalls", "fetched_at": "2026-10-10T00:00:00Z", "data": {}},
            ]
            process_csv(incoming, outgoing, rows, as_of="2026-10-10")
            with outgoing.open(newline="", encoding="utf-8") as handle:
                results = list(csv.DictReader(handle))
        self.assertEqual(results[0]["recall_result"], "uncertain — please check")

    def test_recall_page_contains_distinct_real_fields_and_source_link(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = generate_pages([self.recall], directory)
            self.assertEqual(len(pages), 1)
            html = Path(pages[0]).read_text(encoding="utf-8")
        for text in ("24001", "2026-09-01", "BL-100", self.recall["source_url"]):
            self.assertIn(text, html)
        self.assertIn("rel=\"noopener noreferrer\"", html)

    def test_recall_page_escapes_source_content(self):
        recall = {**self.recall, "data": {**self.recall["data"], "Title": "<script>alert(1)</script>"}}
        with tempfile.TemporaryDirectory() as directory:
            page = Path(generate_pages([recall], directory)[0]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_nhtsa_flat_file_fields_make_a_direct_campaign_citation(self):
        row = {
            "source_id": "nhtsa_recalls",
            "record_id": "321600",
            "source_url": "https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip",
            "data": {"CAMPNO": "26V652000", "MAKETXT": "E-ONE", "MODELTXT": "TYPHOON N", "YEARTXT": "2026", "MFGNAME": "E-One Incorporated"},
        }
        result = match_item({"brand": "E-ONE", "model": "Typhoon N", "model_year": "2026"}, [row], as_of="2026-10-10")
        self.assertEqual(result["result"], "match")
        self.assertEqual(result["recalls"][0]["official_url"], "https://api.nhtsa.gov/recalls/campaignNumber?campaignNumber=26V652000")

    def test_vehicle_model_year_prevents_cross_year_match(self):
        recalled_2026 = {
            "source_id": "nhtsa_recalls",
            "record_id": "321600",
            "data": {"CAMPNO": "26V652000", "MAKETXT": "E-ONE", "MODELTXT": "TYPHOON N", "YEARTXT": "2026"},
        }
        result = match_item({"brand": "E-ONE", "model": "Typhoon N", "model_year": "2025"}, [recalled_2026], as_of="2026-10-10")
        self.assertEqual(result["result"], "no match found in CPSC, NHTSA, FDA and FSIS as of 2026-10-10")

    def test_nhtsa_summary_mention_of_another_model_stays_uncertain(self):
        row = {
            "source_id": "nhtsa_recalls",
            "record_id": "26V000001",
            "data": {"CAMPNO": "26V000001", "MAKETXT": "MERCEDES-BENZ", "MODELTXT": "AMG GT 63", "YEARTXT": "2026", "DESC_DEFECT": "Certain AMG GT 63 vehicles; not the AMG GT base model."},
        }
        result = match_item({"brand": "Mercedes-Benz", "model": "AMG GT", "model_year": "2026"}, [row], as_of="2026-10-10")
        self.assertEqual(result["result"], "uncertain — please check")


if __name__ == "__main__":
    unittest.main()
