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
        self.assertEqual(result["result"], "no match in CPSC, NHTSA, FDA and FSIS as of 2026-10-10")

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

    def test_owner_steps_link_store_secrets_and_require_host_choice(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
        steps = {step["id"]: step for step in manifest["your_steps"]}
        self.assertIn("https://chrome.google.com/webstore/devconsole", steps["submit-extension"]["links"])
        self.assertIn("#/settings/secrets", steps["configure-plans"]["links"])
        self.assertIn("Choose and configure a public host", steps["review-first-pages"]["detail"])

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


if __name__ == "__main__":
    unittest.main()
