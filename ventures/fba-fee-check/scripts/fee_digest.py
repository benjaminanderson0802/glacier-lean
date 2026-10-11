"""Compare seller-provided FBA per-unit fee expectations with Settlement V2 rows."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


CENT = Decimal("0.01")
DISCLAIMER = "Estimate for manual review; not a fee refund guarantee."
REQUIRED_REPORT_COLUMNS = {
    "settlement-id",
    "transaction-type",
    "order-id",
    "fulfillment-id",
    "amount-type",
    "amount-description",
    "amount",
    "currency",
    "sku",
    "quantity-purchased",
}
FBA_FEE_DESCRIPTIONS = {"FBAPerUnitFulfillmentFee", "FBAWeightBasedFee"}


def _money(value: str, *, context: str) -> Decimal:
    """Parse a USD decimal amount, rejecting locale-ambiguous values."""
    normalized = (value or "").strip().replace("$", "")
    if "," in normalized:
        # Settlement V2 uses local currency formatting. This pilot is USD-only;
        # accepting comma decimals/thousands without locale metadata is unsafe.
        raise ValueError(f"{context}: comma-formatted amount is unsupported; use a USD report")
    try:
        return Decimal(normalized).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{context}: invalid amount {value!r}") from None


def _read_expected(schedule_path: Path) -> dict[str, dict[str, str]]:
    expected: dict[str, dict[str, str]] = {}
    with schedule_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"sku", "size_tier", "expected_fee_usd_per_unit", "unit_cost_usd"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = ", ".join(sorted(required - set(reader.fieldnames or [])))
            raise ValueError(f"expected-fee CSV is missing columns: {missing}")
        for line, row in enumerate(reader, start=2):
            sku = (row.get("sku") or "").strip()
            if not sku:
                raise ValueError(f"expected-fee CSV line {line}: sku is required")
            if sku in expected:
                raise ValueError(f"expected-fee CSV line {line}: duplicate SKU {sku!r}")
            _money(row.get("expected_fee_usd_per_unit", ""), context=f"expected-fee CSV line {line} fee")
            _money(row.get("unit_cost_usd", ""), context=f"expected-fee CSV line {line} unit cost")
            expected[sku] = {
                "size_tier": (row.get("size_tier") or "").strip(),
                "expected_fee_usd_per_unit": row["expected_fee_usd_per_unit"].strip(),
                "unit_cost_usd": row["unit_cost_usd"].strip(),
            }
    return expected


def _q(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def analyze_reports(report_path: str | Path, schedule_path: str | Path) -> list[dict[str, str]]:
    """Return one row per FBA fulfillment-fee line in a USD Settlement V2 TSV.

    The expected fee and item cost are supplied by the seller in a separate CSV.
    No fee table is inferred from an Amazon product listing or third-party data.
    """
    report_path = Path(report_path)
    schedule = _read_expected(Path(schedule_path))
    sales: dict[tuple[str, str, str], Decimal] = {}
    source_rows: list[tuple[int, dict[str, str]]] = []

    with report_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream, dialect="excel-tab")
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_REPORT_COLUMNS - columns
        if missing:
            raise ValueError(f"Settlement V2 TSV is missing columns: {', '.join(sorted(missing))}")

        for line, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            if (row.get("currency") or "").strip().upper() != "USD":
                raise ValueError(f"report line {line}: only USD reports are supported")
            if (row.get("fulfillment-id") or "").strip() != "AFN":
                continue
            txn = (row.get("transaction-type") or "").strip()
            description = (row.get("amount-description") or "").strip()
            sku = (row.get("sku") or "").strip()
            order = (row.get("order-id") or "").strip()
            if txn == "Order" and (row.get("amount-type") or "").strip() == "ItemPrice" and description == "Principal" and sku:
                amount = _money(row.get("amount", ""), context=f"report line {line} sale amount")
                key = ((row.get("settlement-id") or "").strip(), order, sku)
                sales[key] = sales.get(key, Decimal("0")) + amount
            if txn == "Order" and description in FBA_FEE_DESCRIPTIONS:
                source_rows.append((line, row))

    results: list[dict[str, str]] = []
    for line, row in source_rows:
        sku = (row.get("sku") or "").strip()
        order = (row.get("order-id") or "").strip()
        settlement_id = (row.get("settlement-id") or "").strip()
        description = (row.get("amount-description") or "").strip()
        try:
            actual = abs(_money(row.get("amount", ""), context=f"report line {line} fee amount"))
        except ValueError as exc:
            raise ValueError(f"report line {line}: invalid fee amount: {exc}") from None
        try:
            quantity = int((row.get("quantity-purchased") or "").strip())
        except ValueError:
            quantity = 0
        expected_row = schedule.get(sku)
        result = {
            "settlement_id": settlement_id,
            "source_report_row": str(line),
            "source_order_id": order,
            "source_shipment_id": (row.get("shipment-id") or "").strip(),
            "source_order_item_code": (row.get("order-item-code") or "").strip(),
            "source_transaction_type": "Order",
            "sku": sku,
            "size_tier": expected_row["size_tier"] if expected_row else "",
            "fee_description": description,
            "quantity": quantity if quantity else "",
            "expected_fee_usd": "",
            "actual_fee_usd": _q(actual),
            "variance_usd": "",
            "estimated_unit_margin_usd": "",
            "observed_unit_margin_usd": "",
            "expected_unit_margin_usd": "",
            "flag": "uncertain_missing_expected_fee",
            "disclaimer": DISCLAIMER,
        }
        if expected_row and quantity > 0:
            expected_per_unit = _money(expected_row["expected_fee_usd_per_unit"], context=f"expected-fee CSV SKU {sku} fee")
            unit_cost = _money(expected_row["unit_cost_usd"], context=f"expected-fee CSV SKU {sku} unit cost")
            expected_total = expected_per_unit * quantity
            variance = actual - expected_total
            result["expected_fee_usd"] = _q(expected_total)
            result["variance_usd"] = _q(variance)
            result["flag"] = "within_expected" if abs(variance) <= CENT else (
                "higher_than_expected" if variance > 0 else "lower_than_expected"
            )
            sale = sales.get((settlement_id, order, sku))
            if sale is not None:
                result["expected_unit_margin_usd"] = _q(sale / quantity - unit_cost - expected_per_unit)
                result["estimated_unit_margin_usd"] = result["expected_unit_margin_usd"]
                result["observed_unit_margin_usd"] = _q(sale / quantity - unit_cost - actual / quantity)
        elif not quantity:
            result["flag"] = "uncertain_missing_quantity"
        results.append(result)
    return results


OUTPUT_COLUMNS = [
    "settlement_id", "source_report_row", "source_order_id", "source_shipment_id",
    "source_order_item_code", "source_transaction_type", "sku", "size_tier",
    "fee_description", "quantity", "expected_fee_usd", "actual_fee_usd",
    "variance_usd", "expected_unit_margin_usd", "estimated_unit_margin_usd",
    "observed_unit_margin_usd", "flag", "disclaimer",
]


def write_digest(report_path: str | Path, schedule_path: str | Path, output_path: str | Path) -> None:
    rows = analyze_reports(report_path, schedule_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare a USD Amazon Settlement V2 report to a seller fee schedule.")
    parser.add_argument("settlement_tsv", type=Path)
    parser.add_argument("expected_fees_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    write_digest(args.settlement_tsv, args.expected_fees_csv, args.output_csv)
    print(f"Wrote fee variance digest: {args.output_csv}")


if __name__ == "__main__":
    main()
