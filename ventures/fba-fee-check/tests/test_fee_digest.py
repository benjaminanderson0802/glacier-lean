import csv
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fee_digest import analyze_reports, write_digest  # noqa: E402


def test_flags_actual_fba_fee_variance_and_estimates_margin_impact():
    results = analyze_reports(
        ROOT / "tests/fixtures/settlement-v2.tsv",
        ROOT / "tests/fixtures/expected-fees.csv",
    )

    assert len(results) == 2
    high = next(row for row in results if row["sku"] == "MUG-12OZ")
    assert high["size_tier"] == "Large standard-size"
    assert high["quantity"] == 2
    assert high["expected_fee_usd"] == "10.00"
    assert high["actual_fee_usd"] == "12.40"
    assert high["variance_usd"] == "2.40"
    assert high["estimated_unit_margin_usd"] == "2.99"
    assert high["flag"] == "higher_than_expected"
    assert high["source_order_id"] == "111-1111111-1111111"


def test_ignores_non_fulfillment_fees_and_non_order_transactions():
    results = analyze_reports(
        ROOT / "tests/fixtures/settlement-v2.tsv",
        ROOT / "tests/fixtures/expected-fees.csv",
    )
    descriptions = {row["fee_description"] for row in results}
    assert descriptions == {"FBAPerUnitFulfillmentFee"}
    assert all(row["source_transaction_type"] == "Order" for row in results)


def test_unknown_sku_is_reported_as_uncertain_instead_of_dropped(tmp_path):
    report = tmp_path / "report.tsv"
    report.write_text(
        "settlement-id\ttransaction-type\torder-id\tfulfillment-id\tamount-type\tamount-description\tamount\tcurrency\tsku\tquantity-purchased\n"
        "123\tOrder\tORDER-1\tAFN\tItemFees\tFBAPerUnitFulfillmentFee\t-3.00\tUSD\tNEW-SKU\t1\n",
        encoding="utf-8",
    )
    schedule = tmp_path / "expected.csv"
    schedule.write_text("sku,size_tier,expected_fee_usd_per_unit,unit_cost_usd\n", encoding="utf-8")

    [row] = analyze_reports(report, schedule)
    assert row["flag"] == "uncertain_missing_expected_fee"
    assert row["variance_usd"] == ""


def test_writes_one_source_linked_csv_digest(tmp_path):
    output = tmp_path / "digest.csv"
    write_digest(
        ROOT / "tests/fixtures/settlement-v2.tsv",
        ROOT / "tests/fixtures/expected-fees.csv",
        output,
    )

    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert rows[0]["source_report_row"]
    assert rows[0]["disclaimer"] == "Estimate for manual review; not a fee refund guarantee."


def test_rejects_unsupported_currency_and_malformed_fee_amount(tmp_path):
    report = tmp_path / "report.tsv"
    report.write_text(
        "settlement-id\ttransaction-type\torder-id\tfulfillment-id\tamount-type\tamount-description\tamount\tcurrency\tsku\tquantity-purchased\n"
        "123\tOrder\tORDER-1\tAFN\tItemFees\tFBAPerUnitFulfillmentFee\tinvalid\tUSD\tMUG-12OZ\t1\n",
        encoding="utf-8",
    )
    schedule = ROOT / "tests/fixtures/expected-fees.csv"
    with pytest.raises(ValueError, match="line 2.*amount"):
        analyze_reports(report, schedule)
