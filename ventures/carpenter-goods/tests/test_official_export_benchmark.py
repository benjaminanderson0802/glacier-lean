"""A public-schema benchmark for Shopify's documented multiline order CSVs.

The headers and row layout follow Shopify's official export documentation:
https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders
Values and order IDs below are synthetic; Shopify does not publish customer
order records for use as a benchmark.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "listing_prep.py"


def test_shopify_multiline_order_export_counts_each_paid_order_once():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        shopify = folder / "shopify-orders.csv"
        shopify.write_text(
            "Name,Financial Status,Total,Lineitem name\n"
            "#1001,paid,600.00,Walnut table\n"
            ",,,Matching bench\n"
            "#1002,refunded,90.00,Sample shelf\n",
            encoding="utf-8",
        )
        output = folder / "commission.json"
        subprocess.run(
            [sys.executable, str(SCRIPT), "commissions", "--shopify-csv", str(shopify),
             "--rate", "0.1", "--output", str(output)],
            check=True, capture_output=True, text=True,
        )

        report = json.loads(output.read_text(encoding="utf-8"))

    assert report["eligible_sales"] == 1
    assert report["gross_sales"] == 600.0
    assert report["commission_due"] == 60.0
    assert report["eligible_orders"][0]["order_id"] == "#1001"
    assert len(report["excluded_orders"]) == 1
    assert any(row["order_id"] == "#1002" for row in report["excluded_orders"])
