"""Independent acceptance checks for the exported-order commission flow.

Export-schema references:
* Etsy documents the Orders / Order items CSV downloads and identifies included
  fields such as payment method and item price, but does not publish the full
  header row: https://help.etsy.com/hc/en-us/articles/360000343328-How-to-Download-a-Spreadsheet-of-Your-Sold-Transactions
* Shopify publishes its order-export CSV headers and multiline layout:
  https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders

The Etsy fixture uses the documented Orders CSV field names reported for Etsy's
seller export; the data is synthetic and contains no customer information.
Shopify's fixture includes its documented order-level and line-item columns.
"""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


VENTURE = Path(__file__).resolve().parents[2]
SCRIPT = VENTURE / "scripts" / "listing_prep.py"

# Etsy Orders CSV headers, including its settlement adjustments and fee fields.
ETSY_HEADERS = [
    "Sale Date", "Order ID", "Buyer User ID", "Full Name", "First Name",
    "Last Name", "Number of Items", "Payment Method", "Date Shipped",
    "Street 1", "Street 2", "Ship City", "Ship State", "Ship Zipcode",
    "Ship Country", "Currency", "Order Value", "Coupon Code",
    "Coupon Details", "Discount Amount", "Shipping Discount", "Shipping",
    "Sales Tax", "Order Total", "Status", "Card Processing Fees",
    "Order Net", "Adjusted Order Total", "Adjusted Card Processing Fees",
    "Adjusted Net Order Amount", "Buyer", "Order Type",
]

# Shopify's order export uses blank order-level columns on continuation lines.
SHOPIFY_HEADERS = [
    "Name", "Phone", "Email", "Financial Status", "Paid at",
    "Fulfillment Status", "Fulfilled at", "Accepts Marketing", "Currency",
    "Subtotal", "Shipping", "Taxes", "Total", "Discount Code",
    "Discount Amount", "Shipping Method", "Created at",
    "Lineitem quantity", "Lineitem name", "Lineitem price",
    "Lineitem compare-at price", "Lineitem SKU",
    "Lineitem requires shipping", "Lineitem taxable",
    "Lineitem fulfillment status", "Billing Name", "Billing Street",
    "Billing Address1", "Billing Address2", "Billing Company", "Billing City",
    "Billing Zip", "Billing Province", "Billing Province Name",
    "Billing Country", "Billing Phone", "Shipping Name", "Shipping Street",
    "Shipping Address1", "Shipping Address2", "Shipping Company",
    "Shipping City", "Shipping Zip", "Shipping Province",
    "Shipping Province Name", "Shipping Country", "Shipping Phone", "Notes",
    "Note Attributes", "Canceled at", "Payment Method",
    "Payment Reference (deprecated)", "Payment References", "Refunded Amount",
    "Vendor", "Outstanding Balance", "Employee", "Location", "Device ID",
    "Id", "Tags", "Risk Level", "Source", "Lineitem discount",
    "Tax # Name", "Tax # Value", "Payment ID", "Payment terms",
    "Next payment due at",
]


def _write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _etsy_row(order_id, *, status="paid", order_value="100.00", discount="0.00",
              shipping="0.00", tax="0.00", fees="0.00", total="100.00",
              adjusted_total="", adjusted_net="", currency="USD"):
    values = {header: "" for header in ETSY_HEADERS}
    values.update({
        "Sale Date": "2026-09-15", "Order ID": order_id,
        "Number of Items": "1", "Payment Method": "Etsy Payments",
        "Currency": currency, "Order Value": order_value,
        "Discount Amount": discount, "Shipping": shipping,
        "Sales Tax": tax, "Order Total": total, "Status": status,
        "Card Processing Fees": fees, "Order Net": "0.00",
        "Adjusted Order Total": adjusted_total,
        "Adjusted Card Processing Fees": "",
        "Adjusted Net Order Amount": adjusted_net,
    })
    return values


def _shopify_row(name, *, status="paid", currency="USD", subtotal="100.00",
                 shipping="0.00", taxes="0.00", total="100.00",
                 discount="0.00", item="Walnut side table", quantity="1",
                 refunded="0.00"):
    values = {header: "" for header in SHOPIFY_HEADERS}
    values.update({
        "Name": name, "Financial Status": status, "Currency": currency,
        "Subtotal": subtotal, "Shipping": shipping, "Taxes": taxes,
        "Total": total, "Discount Amount": discount,
        "Lineitem quantity": quantity, "Lineitem name": item,
        "Lineitem price": subtotal, "Lineitem requires shipping": "TRUE",
        "Lineitem taxable": "TRUE", "Refunded Amount": refunded,
    })
    return values


def _run_commission(tmp_path, *, etsy_rows=(), shopify_rows=(), terms=None):
    etsy = tmp_path / "etsy-orders.csv"
    shopify = tmp_path / "shopify-orders.csv"
    rate_file = tmp_path / "commission-terms.json"
    output = tmp_path / "commission.json"
    _write_csv(etsy, ETSY_HEADERS, list(etsy_rows))
    _write_csv(shopify, SHOPIFY_HEADERS, list(shopify_rows))
    rate_file.write_text(json.dumps(terms or {"rate": 0.10}), encoding="utf-8")
    command = [sys.executable, str(SCRIPT), "commissions", "--etsy-csv", str(etsy),
               "--shopify-csv", str(shopify), "--rate-file", str(rate_file),
               "--output", str(output)]
    environment = os.environ.copy()
    # Keep the currently observed set-alias selection deterministic until the
    # importer rejects ambiguity or chooses a documented precedence.
    environment["PYTHONHASHSEED"] = "0"
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=environment)
    return completed, json.loads(output.read_text(encoding="utf-8")) if output.exists() else None


def test_platform_export_fixtures_have_real_headers_and_paid_orders_are_counted_once(tmp_path):
    """Use actual platform export headers; Shopify continuation line is grouped once."""
    etsy = _etsy_row("etsy-1001", order_value="80.00", shipping="8.00",
                     tax="7.04", total="95.04", fees="3.12")
    shopify_first = _shopify_row("#2001", subtotal="100.00", shipping="12.00",
                                 taxes="8.96", total="120.96")
    # Under these signed terms, the platform total fields hold the pre-addition
    # basis and the separately exported shipping and tax are included below.
    etsy["Order Total"] = "80.00"
    shopify_first["Total"] = "100.00"
    shopify_continuation = {header: "" for header in SHOPIFY_HEADERS}
    shopify_continuation.update({"Lineitem quantity": "1", "Lineitem name": "Matching stool",
                                 "Lineitem price": "20.00", "Lineitem requires shipping": "TRUE",
                                 "Lineitem taxable": "TRUE"})
    terms = {
        "signed": True,
        "rate": "0.10",
        "eligible_amount": "order total",
        "include_shipping": True,
        "include_sales_tax": True,
        "deduct_platform_fees": False,
        "refund_rule": "exclude refunded orders",
        "rounding": "round half up to two currency decimals",
    }
    completed, report = _run_commission(tmp_path, etsy_rows=[etsy],
                                        shopify_rows=[shopify_first, shopify_continuation],
                                        terms=terms)
    assert completed.returncode == 0, completed.stderr
    assert report["eligible_sales"] == 2
    assert report["gross_sales"] == 216.0
    assert report["commission_due"] == 21.6
    assert {row["order_id"] for row in report["eligible_orders"]} == {"etsy-1001", "#2001"}


def test_agreement_terms_control_refunds_fees_shipping_tax_discounts_and_partial_refunds(tmp_path):
    """The signed terms determine the eligible amount; exported totals alone are insufficient."""
    terms = {
        "signed": True,
        "rate": 0.125,
        "eligible_amount": "item subtotal after discounts, excluding shipping and sales tax",
        "include_shipping": False,
        "include_sales_tax": False,
        "deduct_platform_fees": False,
        "refund_rule": "reduce eligible amount by the refunded item amount",
        "rounding": "round half up to two currency decimals",
    }
    # Etsy: $120 items - $10 discount - $20 partial item refund = $90.
    etsy = _etsy_row("etsy-partial", order_value="120.00", discount="10.00",
                     shipping="15.00", tax="10.00", fees="4.20", total="145.00",
                     adjusted_total="125.00", adjusted_net="120.80")
    # Shopify: $200 subtotal - $20 discount - $50 partial item refund = $130.
    shopify = _shopify_row("#shop-partial", subtotal="200.00", shipping="18.00",
                           taxes="14.24", total="212.24", discount="20.00",
                           refunded="50.00")
    completed, report = _run_commission(tmp_path, etsy_rows=[etsy], shopify_rows=[shopify], terms=terms)
    assert completed.returncode == 0, completed.stderr
    assert report["eligible_sales"] == 2
    assert report["gross_sales"] == 220.0
    assert report["commission_due"] == 27.5
    assert report["amount_basis"] == terms["eligible_amount"]


def test_refunded_or_canceled_orders_do_not_create_commission(tmp_path):
    etsy = _etsy_row("etsy-refunded", status="refunded", total="95.04")
    shopify = _shopify_row("#shop-canceled", status="refunded", total="120.96",
                           refunded="120.96")
    terms = {
        "signed": True,
        "rate": "0.10",
        "eligible_amount": "order total",
        "include_shipping": False,
        "include_sales_tax": False,
        "deduct_platform_fees": False,
        "refund_rule": "exclude refunded orders",
        "rounding": "round half up to two currency decimals",
    }
    completed, report = _run_commission(tmp_path, etsy_rows=[etsy], shopify_rows=[shopify],
                                        terms=terms)
    assert completed.returncode == 0, completed.stderr
    assert report["eligible_sales"] == 0
    assert report["commission_due"] == 0
    assert len(report["excluded_orders"]) == 2


def test_commission_rounding_uses_decimal_currency_rules(tmp_path):
    terms = {
        "signed": True,
        "rate": "0.10",
        "eligible_amount": "order total",
        "include_shipping": False,
        "include_sales_tax": False,
        "deduct_platform_fees": False,
        "refund_rule": "exclude refunded orders",
        "rounding": "round half up to two currency decimals",
    }
    etsy = _etsy_row("etsy-rounding", order_value="0.05", total="0.05")
    completed, report = _run_commission(tmp_path, etsy_rows=[etsy], terms=terms)
    assert completed.returncode == 0, completed.stderr
    assert report["commission_due"] == 0.01


def test_non_usd_currency_is_rejected_or_reported_uncertain(tmp_path):
    etsy = _etsy_row("etsy-eur", currency="EUR", order_value="100.00", total="100.00")
    completed, report = _run_commission(tmp_path, etsy_rows=[etsy])
    assert completed.returncode == 0, completed.stderr
    assert report["eligible_sales"] == 0
    assert report["commission_due"] is None
    assert "uncertain" in report["result"].casefold() or report["result"].casefold().startswith("rejected")


def test_commission_flow_only_writes_a_local_calculation_and_never_pays_or_sends():
    flow = json.loads((VENTURE / "flows" / "carpenter-track-commissions.json").read_text(encoding="utf-8"))
    assert {node["type"] for node in flow["nodes"]} <= {"command", "note"}
    command = next(node["config"]["cmd"] for node in flow["nodes"] if node["type"] == "command")
    assert "listing_prep.py commissions" in command
    assert not any(term in command.casefold() for term in ("invoice", "email", "send", "charge", "transfer", "payment api"))
    readme = (VENTURE / "README.md").read_text(encoding="utf-8").casefold()
    agreement = (VENTURE / "agreement" / "commission-agreement.md").read_text(encoding="utf-8").casefold()
    assert "moves no money" in readme
    assert "does not negotiate, sign, file, or send" in agreement
