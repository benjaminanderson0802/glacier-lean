"""Independent frozen cases for the signed commission basis.

All rows below are synthetic. Etsy's seller export instructions identify the
Orders CSV and example fields but do not publish its complete header row;
Shopify documents its order-export headers and blank continuation rows:
https://help.etsy.com/hc/en-us/articles/360035753053-How-Do-I-Download-My-Etsy-Data
https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders

The ``signed`` marker in the terms fixture represents a separately supplied
agreement signed by both parties. An export or a rate alone is not that proof.
"""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


VENTURE = Path(__file__).resolve().parents[2]
SCRIPT = VENTURE / "scripts" / "listing_prep.py"
ETSY_HEADERS = [
    "Order ID", "Status", "Currency", "Order Value", "Order Total",
    "Total", "Discount Amount", "Shipping", "Sales Tax", "Card Processing Fees",
    "Adjusted Order Total",
]
SHOPIFY_HEADERS = [
    "Name", "Financial Status", "Currency", "Subtotal", "Shipping", "Taxes",
    "Total", "Discount Amount", "Refunded Amount", "Lineitem quantity",
    "Lineitem name", "Lineitem price",
]


def _row(headers, **values):
    return {header: values.get(header, "") for header in headers}


def _etsy(order_id, *, status="paid", currency="USD", item="100.00", total="120.00",
          duplicate_total="", discount="0.00", shipping="10.00", tax="10.00",
          fees="2.00", adjusted=""):
    return _row(ETSY_HEADERS, **{
        "Order ID": order_id, "Status": status, "Currency": currency,
        "Order Value": item, "Order Total": total, "Total": duplicate_total,
        "Discount Amount": discount, "Shipping": shipping, "Sales Tax": tax,
        "Card Processing Fees": fees, "Adjusted Order Total": adjusted,
    })


def _shopify(order_id, *, status="paid", currency="USD", subtotal="100.00",
             total="120.00", discount="0.00", shipping="10.00", taxes="10.00",
             refunded="0.00"):
    return _row(SHOPIFY_HEADERS, **{
        "Name": order_id, "Financial Status": status, "Currency": currency,
        "Subtotal": subtotal, "Shipping": shipping, "Taxes": taxes,
        "Total": total, "Discount Amount": discount, "Refunded Amount": refunded,
        "Lineitem quantity": "1", "Lineitem name": "Synthetic furniture item",
        "Lineitem price": subtotal,
    })


def _run(tmp_path, *, etsy=(), shopify=(), terms=None):
    etsy_path = tmp_path / "etsy-orders.csv"
    shopify_path = tmp_path / "shopify-orders.csv"
    terms_path = tmp_path / "terms.json"
    output_path = tmp_path / "commission.json"
    for path, headers, rows in (
        (etsy_path, ETSY_HEADERS, etsy),
        (shopify_path, SHOPIFY_HEADERS, shopify),
    ):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    terms_path.write_text(json.dumps(terms or {}), encoding="utf-8")
    env = os.environ.copy()
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "commissions", "--etsy-csv", str(etsy_path),
         "--shopify-csv", str(shopify_path), "--rate-file", str(terms_path),
         "--output", str(output_path)],
        capture_output=True, text=True, check=False, env=env,
    )
    report = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
    return completed, report


def _signed_terms(**overrides):
    terms = {
        "signed": True,
        "rate": "0.125",
        "eligible_amount": "item subtotal after discounts",
        "include_shipping": False,
        "include_sales_tax": False,
        "deduct_platform_fees": False,
        "refund_rule": "reduce eligible amount by the refunded item amount",
        "rounding": "round half up to two currency decimals",
    }
    terms.update(overrides)
    return terms


def _assert_uncertain_without_payable_amount(completed, report):
    assert completed.returncode == 0, completed.stderr
    assert report is not None
    assert "uncertain" in report["result"].casefold()
    assert report["commission_due"] is None
    assert report["eligible_sales"] == 0
    assert report["eligible_orders"] == []


def test_signed_item_basis_uses_discounted_items_and_excludes_shipping_tax_and_fees(tmp_path):
    # $100 items - $10 discount = $90 basis; $10 shipping, $10 tax, and $2 fee
    # do not change the stated basis. The final commission is $11.25.
    etsy = _etsy("etsy-signed", item="100.00", total="110.00", discount="10.00",
                 shipping="10.00", tax="10.00", fees="2.00", adjusted="110.00")
    completed, report = _run(tmp_path, etsy=[etsy], terms=_signed_terms())
    assert completed.returncode == 0, completed.stderr
    assert report["amount_basis"] == "item subtotal after discounts"
    assert report["gross_sales"] == 90.0
    assert report["commission_due"] == 11.25


@pytest.mark.parametrize("terms", [
    {"rate": "0.125"},
    {**_signed_terms(), "signed": False},
])
def test_missing_or_unsigned_terms_never_create_a_payable_amount(tmp_path, terms):
    completed, report = _run(
        tmp_path, etsy=[_etsy("etsy-no-signature", adjusted="120.00")], terms=terms
    )
    _assert_uncertain_without_payable_amount(completed, report)


@pytest.mark.parametrize("missing", [
    "rate", "eligible_amount", "include_shipping", "include_sales_tax",
    "deduct_platform_fees", "refund_rule", "rounding",
])
def test_incomplete_signed_terms_never_create_a_payable_amount(tmp_path, missing):
    terms = _signed_terms()
    del terms[missing]
    completed, report = _run(tmp_path, etsy=[_etsy("etsy-incomplete")], terms=terms)
    if missing == "rate":
        assert completed.returncode != 0
        assert report is None
    else:
        _assert_uncertain_without_payable_amount(completed, report)


def test_conflicting_order_amount_columns_are_uncertain_even_with_signed_basis(tmp_path):
    # Both columns claim the order total but disagree. The signed terms name the
    # order-total basis, but the export still does not identify which value is true.
    row = _etsy("etsy-conflicting-columns", total="120.00", duplicate_total="121.00",
                 adjusted="120.00")
    terms = _signed_terms(eligible_amount="order total", refund_rule="exclude refunded orders")
    completed, report = _run(tmp_path, etsy=[row], terms=terms)
    _assert_uncertain_without_payable_amount(completed, report)


def test_mixed_currencies_are_uncertain_and_never_combined(tmp_path):
    completed, report = _run(
        tmp_path,
        etsy=[_etsy("etsy-usd", currency="USD")],
        shopify=[_shopify("#shop-eur", currency="EUR")],
        terms=_signed_terms(),
    )
    _assert_uncertain_without_payable_amount(completed, report)
    assert any("mixed currenc" in reason.casefold() for reason in report["uncertainty_reasons"])


def test_unsupported_single_currency_is_uncertain_without_conversion_terms(tmp_path):
    completed, report = _run(
        tmp_path, etsy=[_etsy("etsy-eur", currency="EUR")], terms=_signed_terms()
    )
    _assert_uncertain_without_payable_amount(completed, report)
    assert any("unsupported currency EUR" in reason for reason in report["uncertainty_reasons"])


def test_partial_and_full_refunds_follow_signed_refund_rule(tmp_path):
    partial = _shopify("#shop-partial", subtotal="100.00", discount="10.00", refunded="20.00")
    full = _shopify("#shop-full", status="refunded", subtotal="100.00", refunded="100.00")
    completed, report = _run(tmp_path, shopify=[partial, full], terms=_signed_terms())
    assert completed.returncode == 0, completed.stderr
    assert report["eligible_sales"] == 1
    assert report["gross_sales"] == 70.0
    assert report["commission_due"] == 8.75
    assert len(report["excluded_orders"]) == 1


def test_signed_rounding_is_applied_to_final_commission_in_minor_units(tmp_path):
    terms = _signed_terms(rate="0.10", eligible_amount="order total", refund_rule="exclude refunded orders")
    # Exact commission is 0.005 USD; signed half-up rule yields 0.01 USD.
    row = _etsy("etsy-half-cent", item="0.05", total="0.05", shipping="0.00", tax="0.00", fees="0.00")
    completed, report = _run(tmp_path, etsy=[row], terms=terms)
    assert completed.returncode == 0, completed.stderr
    assert report["commission_due"] == 0.01
    assert report["payment_status"] == "calculated only; no invoice, charge, or transfer was made"
