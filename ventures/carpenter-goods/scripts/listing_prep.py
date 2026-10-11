"""Prepare reviewable listing drafts and commission summaries without publishing."""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def prepare_listing(product: dict[str, Any], comparables: list[dict[str, Any]], *, as_of: date | None = None) -> dict[str, Any]:
    """Create Etsy and Shopify copy from owner facts and completed-sale evidence."""
    required = ("product_id", "name", "category", "description", "pickup_area", "photos")
    missing = [key for key in required if key not in product or product[key] in (None, "")]
    if missing:
        raise ValueError(f"product is missing required fields: {', '.join(missing)}")
    if not isinstance(product["photos"], list):
        raise ValueError("photos must be a list of local photo paths")

    category = str(product["category"]).strip().casefold()
    today = as_of or date.today()
    source_counts: dict[str, int] = {}
    for row in comparables:
        if not isinstance(row, dict):
            continue
        try:
            parsed = urlparse(str(row.get("source_url", "")))
        except ValueError:
            continue
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            canonical = f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{parsed.path.rstrip('/')}{('?' + parsed.query) if parsed.query else ''}"
            source_counts[canonical] = source_counts.get(canonical, 0) + 1
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for index, row in enumerate(comparables):
        if not isinstance(row, dict):
            rejected.append({"row": str(index), "reason": "row must be an object"})
            continue
        try:
            price = float(row["sold_price"])
            parsed = urlparse(str(row["source_url"]))
        except (KeyError, TypeError, ValueError):
            rejected.append({"row": str(index), "reason": "missing or invalid price/source URL"})
            continue
        canonical = f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{parsed.path.rstrip('/')}{('?' + parsed.query) if parsed.query else ''}"
        if source_counts.get(canonical, 0) > 1:
            reason = "duplicate sale source URL"
        elif not parsed.netloc or parsed.scheme not in {"http", "https"}:
            reason = "source URL must be HTTP or HTTPS"
        elif not isinstance(row.get("sold_date"), str):
            reason = "completed sale date is required"
        else:
            try:
                sold_on = date.fromisoformat(row["sold_date"])
            except ValueError:
                sold_on = None
            if sold_on is None:
                reason = "completed sale date must use YYYY-MM-DD"
            elif sold_on > today:
                reason = "sale date is in the future"
            elif sold_on < today - timedelta(days=365):
                reason = "sale evidence is older than 365 days"
            elif not isinstance(row.get("sold_price"), (int, float)) or isinstance(row.get("sold_price"), bool) or price <= 0:
                reason = "sold price must be a positive number"
            elif row.get("completed") is not True:
                reason = "sale must be confirmed completed"
            elif str(row.get("category", "")).strip().casefold() != category:
                reason = "sale category does not match the product"
            else:
                reason = ""
        if reason:
            rejected.append({"row": str(index), "reason": reason})
        else:
            eligible.append({"source_url": row["source_url"], "sold_price": price, "sold_date": row["sold_date"]})

    enough_comparables = len(eligible) >= 3
    median_price = round(float(statistics.median(row["sold_price"] for row in eligible)), 2) if enough_comparables else None
    materials = product.get("materials", [])
    dimensions = product.get("dimensions", "")
    condition = product.get("condition", "")
    details = [str(value).strip() for value in [*materials, dimensions, condition] if str(value).strip()]
    description = str(product["description"]).strip()
    if details:
        description = f"{description}\n\nDetails supplied by the maker: {', '.join(details)}."

    result = "match" if enough_comparables else "uncertain — please check"
    return {
        "product_id": str(product["product_id"]),
        "result": result,
        "checked_on": today.isoformat(),
        "etsy": {"title": str(product["name"]).strip(), "description": description,
                 "price": median_price, "pickup_area": str(product["pickup_area"]).strip(),
                 "photos": list(product["photos"])},
        "shopify": {"title": str(product["name"]).strip(), "description": description,
                    "price": median_price, "pickup_area": str(product["pickup_area"]).strip(),
                    "photos": list(product["photos"])},
        "suggested_price": median_price,
        "price_method": "median of owner-supplied completed sales in the same category",
        "price_sources": [row["source_url"] for row in eligible],
        "comparable_count": len(eligible),
        "rejected_comparables": rejected,
        "publish_status": "not published; owner approval and manual publication required",
        "published": False,
    }


def calculate_commissions(sales: list[dict[str, Any]], commission_rate: float) -> dict[str, Any]:
    """Summarize paid sales against the rate agreed in writing with the maker."""
    rate = float(commission_rate)
    if not 0 <= rate <= 1:
        raise ValueError("commission_rate must be between 0 and 1")
    paid = []
    excluded = []
    seen_orders: set[tuple[str, str]] = set()
    for row in sales:
        platform = str(row.get("platform", "Owner export")).strip() or "Owner export"
        order_id = str(row.get("order_id", "")).strip()
        status = str(row.get("status", "")).strip().casefold().replace(" ", "_")
        key = (platform.casefold(), order_id.casefold())
        if order_id and key in seen_orders:
            excluded.append({"platform": platform, "order_id": order_id, "reason": "duplicate order id"})
            continue
        if order_id:
            seen_orders.add(key)
        if status != "paid":
            excluded.append({"platform": platform, "order_id": order_id, "reason": f"status is {status or 'missing'}, not paid"})
            continue
        try:
            amount = float(row["amount"])
        except (KeyError, TypeError, ValueError):
            excluded.append({"platform": platform, "order_id": order_id, "reason": "missing or invalid order total"})
            continue
        if amount > 0:
            paid.append({"platform": platform, "order_id": order_id, "amount": round(amount, 2)})
        else:
            excluded.append({"platform": platform, "order_id": order_id, "reason": "order total must be positive"})
    gross = round(sum(row["amount"] for row in paid), 2)
    return {
        "result": "match" if paid else f"no match found in imported sales as of {date.today().isoformat()}",
        "eligible_sales": len(paid), "eligible_orders": paid, "gross_sales": gross,
        "commission_rate": rate, "commission_due": round(gross * rate, 2),
        "excluded_orders": excluded,
        "source": "owner-exported paid order records; verify against platform settlement records",
        "amount_basis": "exported order total; confirm the written agreement defines treatment of tax, shipping, discounts, refunds, and fees",
        "payment_status": "calculated only; no invoice, charge, or transfer was made",
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 (optionally BOM-prefixed) CSV export."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _csv_product(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    if len(rows) != 1:
        raise ValueError("product sheet CSV must contain exactly one product row")
    row = {str(key).strip().casefold(): (value or "").strip() for key, value in rows[0].items()}
    for field in ("materials", "photos"):
        row[field] = [part.strip() for part in row.get(field, "").split(";") if part.strip()]
    return row


def _header_key(value: str) -> str:
    return " ".join("".join(char.casefold() if char.isalnum() else " " for char in value).split())


def _export_sales(path: Path, platform: str) -> list[dict[str, Any]]:
    """Map order-level Etsy or Shopify export headers to commission input rows."""
    aliases = {
        "order_id": {"order id", "order", "name", "order number"},
        "status": {"order status", "financial status", "payment status", "status"},
        "amount": {"order total", "total order value", "order value", "total"},
    }
    result = []
    for row_number, original in enumerate(_read_csv(path), start=2):
        row = {_header_key(key): value for key, value in original.items() if key}
        mapped = {}
        for field, names in aliases.items():
            value = next((row[name] for name in names if name in row), None)
            if value is None:
                raise ValueError(f"{platform} CSV is missing a recognized {field} column")
            mapped[field] = value.strip()
        amount_text = mapped["amount"].replace(",", "").replace("$", "").strip()
        try:
            amount = float(amount_text)
        except ValueError:
            amount = None
        result.append({
            "platform": platform, "order_id": mapped["order_id"],
            "status": mapped["status"], "amount": amount,
            "source_row": row_number,
        })
    return result


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    listing = subparsers.add_parser("prepare", help="prepare local marketplace drafts")
    product_source = listing.add_mutually_exclusive_group(required=True)
    product_source.add_argument("--product", type=Path, help="JSON product facts")
    product_source.add_argument("--product-csv", type=Path, help="one-row product sheet CSV")
    listing.add_argument("--comparables", type=Path, required=True)
    listing.add_argument("--output", type=Path, required=True)
    commission = subparsers.add_parser("commissions", help="calculate commission from an owner export")
    commission.add_argument("--sales", type=Path, help="JSON owner export")
    commission.add_argument("--etsy-csv", type=Path, help="order-level Etsy CSV export")
    commission.add_argument("--shopify-csv", type=Path, help="order-level Shopify CSV export")
    rate_source = commission.add_mutually_exclusive_group(required=True)
    rate_source.add_argument("--rate", type=float, help="rate agreed in writing with the maker")
    rate_source.add_argument("--rate-file", type=Path, help="JSON file containing the written commission rate")
    commission.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.action == "prepare":
        product = _read_json(args.product) if args.product else _csv_product(args.product_csv)
        result = prepare_listing(product, _read_json(args.comparables))
    else:
        if bool(args.sales) == bool(args.etsy_csv or args.shopify_csv):
            parser.error("provide --sales or one or both of --etsy-csv and --shopify-csv")
        rate = args.rate if args.rate is not None else _read_json(args.rate_file).get("rate")
        if rate is None:
            parser.error("the written commission rate is missing from --rate-file")
        if args.sales:
            sales = _read_json(args.sales)
        else:
            sales = []
            if args.etsy_csv:
                sales.extend(_export_sales(args.etsy_csv, "Etsy"))
            if args.shopify_csv:
                sales.extend(_export_sales(args.shopify_csv, "Shopify"))
        result = calculate_commissions(sales, rate)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(args.output.parent, 0o700)
    except OSError:
        pass
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        os.chmod(args.output, 0o600)
    except OSError:
        pass
    print(json.dumps({"result": result["result"], "output": str(args.output), "published": result.get("published", False)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
