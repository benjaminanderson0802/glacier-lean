import json
import sys
import unittest
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.listing_prep import calculate_commissions, prepare_listing  # noqa: E402


class ListingPrepAcceptanceTests(unittest.TestCase):
    def test_builds_drafts_from_owner_data_and_eligible_completed_comparables(self):
        product = json.loads((ROOT / "tests" / "product.json").read_text(encoding="utf-8"))
        comparables = json.loads((ROOT / "tests" / "comparables.json").read_text(encoding="utf-8"))

        draft = prepare_listing(product, comparables, as_of=date(2026, 10, 10))

        self.assertEqual(draft["result"], "match")
        self.assertEqual(draft["suggested_price"], 425.0)
        self.assertEqual(draft["price_sources"], [row["source_url"] for row in comparables])
        self.assertEqual(draft["etsy"]["title"], "Live edge walnut coffee table")
        self.assertTrue(draft["shopify"]["description"].startswith(product["description"]))
        self.assertFalse(draft["published"])
        self.assertEqual(draft["rejected_comparables"], [])

    def test_missing_comparables_are_uncertain_and_never_invents_price(self):
        product = json.loads((ROOT / "tests" / "product.json").read_text(encoding="utf-8"))

        draft = prepare_listing(product, [], as_of=date(2026, 10, 10))

        self.assertEqual(draft["result"], "uncertain — please check")
        self.assertIsNone(draft["suggested_price"])
        self.assertEqual(draft["price_sources"], [])

    def test_rejects_stale_duplicate_future_and_invalid_sale_evidence_before_median(self):
        product = json.loads((ROOT / "tests" / "product.json").read_text(encoding="utf-8"))
        rows = [
            {"source_url": "https://example.test/sales/a", "category": "coffee table", "completed": True, "sold_price": 100, "sold_date": "2026-09-01"},
            {"source_url": "https://example.test/sales/a", "category": "coffee table", "completed": True, "sold_price": 900, "sold_date": "2026-09-02"},
            {"source_url": "https://example.test/sales/stale", "category": "coffee table", "completed": True, "sold_price": 200, "sold_date": "2024-01-01"},
            {"source_url": "https://example.test/sales/future", "category": "coffee table", "completed": True, "sold_price": 300, "sold_date": "2026-12-01"},
            {"source_url": "https://example.test/sales/invalid", "category": "coffee table", "completed": True, "sold_price": -1, "sold_date": "2026-09-03"},
        ]
        result = prepare_listing(product, rows, as_of=date(2026, 10, 10))
        self.assertEqual(result["result"], "uncertain — please check")
        self.assertIsNone(result["suggested_price"])
        self.assertEqual(result["comparable_count"], 0)
        self.assertEqual(len(result["rejected_comparables"]), 5)

    def test_manifest_links_exact_shop_platform_and_owner_export_instructions(self):
        manifest = json.loads((ROOT / "venture.json").read_text(encoding="utf-8"))
        links = [link for step in manifest["your_steps"] for link in step["links"]]
        details = " ".join(step["detail"] for step in manifest["your_steps"])
        self.assertIn("https://www.etsy.com/your/shops/me/dashboard", links)
        self.assertIn("https://admin.shopify.com/", links)
        self.assertIn("paid-sales.json", details)

    def test_commission_tracker_uses_signed_agreed_rate_and_ignores_unpaid_sales(self):
        sales = [
            {"order_id": "A1", "status": "paid", "amount": 500.0},
            {"order_id": "A2", "status": "refunded", "amount": 300.0},
            {"order_id": "A3", "status": "pending", "amount": 200.0},
        ]

        result = calculate_commissions(sales, commission_rate=0.12)

        self.assertEqual(result["eligible_sales"], 1)
        self.assertEqual(result["commission_due"], 60.0)
        self.assertEqual(result["result"], "match")

    def test_commission_rate_outside_range_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_commissions([], commission_rate=1.5)


if __name__ == "__main__":
    unittest.main()
