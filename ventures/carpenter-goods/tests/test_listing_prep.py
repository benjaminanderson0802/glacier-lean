import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.listing_prep import calculate_commissions, prepare_listing  # noqa: E402


class ListingPrepAcceptanceTests(unittest.TestCase):
    def test_builds_drafts_from_owner_data_and_eligible_completed_comparables(self):
        product = json.loads((ROOT / "tests" / "product.json").read_text(encoding="utf-8"))
        comparables = json.loads((ROOT / "tests" / "comparables.json").read_text(encoding="utf-8"))

        draft = prepare_listing(product, comparables)

        self.assertEqual(draft["result"], "match")
        self.assertEqual(draft["suggested_price"], 425.0)
        self.assertEqual(draft["price_sources"], [row["source_url"] for row in comparables])
        self.assertEqual(draft["etsy"]["title"], "Live edge walnut coffee table")
        self.assertTrue(draft["shopify"]["description"].startswith(product["description"]))
        self.assertFalse(draft["published"])

    def test_missing_comparables_are_uncertain_and_never_invents_price(self):
        product = json.loads((ROOT / "tests" / "product.json").read_text(encoding="utf-8"))

        draft = prepare_listing(product, [])

        self.assertEqual(draft["result"], "uncertain — please check")
        self.assertIsNone(draft["suggested_price"])
        self.assertEqual(draft["price_sources"], [])

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
