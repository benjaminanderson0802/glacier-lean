"""Fixture acceptance coverage for the owner-export CSV workflow."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "listing_prep.py"


class CsvWorkflowAcceptanceTests(unittest.TestCase):
    def test_product_sheet_csv_creates_etsy_and_shopify_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            product = tmp_path / "product.csv"
            with product.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "product_id", "name", "category", "description", "pickup_area",
                    "materials", "dimensions", "condition", "photos",
                ])
                writer.writeheader()
                writer.writerow({
                    "product_id": "table-1", "name": "Walnut table", "category": "coffee table",
                    "description": "Handmade walnut coffee table.", "pickup_area": "Madison, WI",
                    "materials": "walnut; hardwax oil", "dimensions": "40 x 22 x 18 in",
                    "condition": "new", "photos": "photos/front.jpg; photos/side.jpg",
                })
            comparables = tmp_path / "comparables.json"
            comparables.write_text(json.dumps([
                {"source_url": f"https://example.test/sale/{n}", "category": "coffee table",
                 "completed": True, "sold_price": price, "sold_date": "2026-09-01"}
                for n, price in enumerate((400, 425, 450))
            ]), encoding="utf-8")
            output = tmp_path / "listing.json"

            subprocess.run([
                sys.executable, str(SCRIPT), "prepare", "--product-csv", str(product),
                "--comparables", str(comparables), "--output", str(output),
            ], check=True, capture_output=True, text=True)
            draft = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(draft["etsy"]["title"], "Walnut table")
        self.assertEqual(draft["shopify"]["title"], "Walnut table")
        self.assertEqual(draft["suggested_price"], 425.0)
        self.assertEqual(draft["etsy"]["photos"], ["photos/front.jpg", "photos/side.jpg"])
        self.assertFalse(draft["published"])

    def test_etsy_and_shopify_order_exports_produce_combined_paid_commission_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            etsy = tmp_path / "etsy-orders.csv"
            etsy.write_text(
                "Order ID,Order Status,Order Total\nE-1,Paid,500.00\nE-2,Unpaid,90.00\n",
                encoding="utf-8",
            )
            shopify = tmp_path / "shopify-orders.csv"
            shopify.write_text(
                "Name,Financial Status,Total\n#S-1,paid,250.00\n#S-2,refunded,100.00\n",
                encoding="utf-8",
            )
            output = tmp_path / "commission.json"

            subprocess.run([
                sys.executable, str(SCRIPT), "commissions", "--etsy-csv", str(etsy),
                "--shopify-csv", str(shopify), "--rate", "0.12", "--output", str(output),
            ], check=True, capture_output=True, text=True)
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(report["eligible_sales"], 2)
        self.assertEqual(report["gross_sales"], 750.0)
        self.assertEqual(report["commission_due"], 90.0)
        self.assertEqual({row["platform"] for row in report["eligible_orders"]}, {"Etsy", "Shopify"})
        self.assertIn("transfer", report["payment_status"])

    def test_templates_and_agreement_have_owner_blanks_and_not_legal_advice_note(self):
        listing_template = ROOT / "templates" / "product-sheet.csv"
        self.assertTrue(listing_template.exists())
        with listing_template.open(newline="", encoding="utf-8") as handle:
            self.assertIn("name", csv.DictReader(handle).fieldnames)
        for file in (ROOT / "agreement" / "commission-agreement.md",
                     ROOT / "agreement" / "commission-summary.md"):
            self.assertTrue(file.exists())
            content = file.read_text(encoding="utf-8").casefold()
            self.assertIn("not legal advice", content)
            self.assertIn("[", content)


if __name__ == "__main__":
    unittest.main()
