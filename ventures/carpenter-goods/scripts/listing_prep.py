"""Prepare reviewable listing drafts and commission summaries without publishing."""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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


def _money(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _eligible_basis(terms: dict[str, Any]) -> tuple[str | None, str]:
    """Return a supported basis and its report label, or uncertainty reason."""
    named = terms.get("eligible_amount")
    if named is None:
        # Backwards-compatible default for rate-only files: use the platform's
        # explicit order-total field. This is stated in the report and README.
        return "order_total", "exported order total (default when no eligible_amount is specified)"
    normalized = " ".join(re.findall(r"[a-z0-9]+", str(named).casefold()))
    if "item subtotal" in normalized or "subtotal" in normalized:
        if "after discounts" in normalized or terms.get("deduct_discounts") is True:
            return "item_subtotal", str(named)
        return None, "item subtotal does not state whether discounts are deducted"
    if "order total" in normalized:
        return "order_total", str(named)
    return None, "eligible_amount does not identify a supported order total or item subtotal basis"


def _commission_terms_uncertainties(terms: dict[str, Any]) -> list[str]:
    """Require an explicit signed agreement with every supported calculation term."""
    reasons = []
    if terms.get("signed") is not True:
        reasons.append("commission terms are missing proof that both parties signed")
    required = {
        "rate": "commission rate",
        "eligible_amount": "eligible amount basis",
        "include_shipping": "shipping inclusion rule",
        "include_sales_tax": "sales tax inclusion rule",
        "deduct_platform_fees": "platform fee rule",
        "refund_rule": "refund rule",
        "rounding": "rounding rule",
    }
    for key, label in required.items():
        if key not in terms or terms[key] in (None, ""):
            reasons.append(f"signed commission terms are missing the {label}")
    for key in ("include_shipping", "include_sales_tax", "deduct_platform_fees"):
        if key in terms and not isinstance(terms[key], bool):
            reasons.append(f"signed commission {key} must be true or false")
    basis, basis_reason = _eligible_basis(terms)
    if basis is None:
        reasons.append(basis_reason)
    refund_rule = str(terms.get("refund_rule", "")).strip().casefold()
    if refund_rule and not (
        "reduce eligible amount by the refunded item amount" in refund_rule
        or any(word in refund_rule for word in ("exclude", "reverse", "no refund"))
    ):
        reasons.append("unsupported refund rule in written terms")
    rounding = str(terms.get("rounding", "")).strip().casefold()
    if rounding and rounding != "round half up to two currency decimals":
        reasons.append("unsupported rounding rule in written terms")
    return reasons


def calculate_commissions(sales: list[dict[str, Any]], commission_rate: float,
                          terms: dict[str, Any] | None = None) -> dict[str, Any]:
    """Summarize paid sales using the supported basis stated in written terms."""
    terms = terms or {}
    rate = _money(commission_rate)
    if rate is None or not 0 <= rate <= 1:
        raise ValueError("commission_rate must be between 0 and 1")
    basis, basis_label = _eligible_basis(terms)
    paid = []
    excluded = []
    uncertain_reasons = _commission_terms_uncertainties(terms)
    seen_orders: set[tuple[str, str]] = set()
    currencies: set[str] = set()
    for row in sales:
        platform = str(row.get("platform", "Owner export")).strip() or "Owner export"
        order_id = str(row.get("order_id", "")).strip()
        status = str(row.get("status", "")).strip().casefold().replace("-", "_").replace(" ", "_")
        key = (platform.casefold(), order_id.casefold())
        if order_id and key in seen_orders:
            excluded.append({"platform": platform, "order_id": order_id, "reason": "duplicate order id"})
            continue
        if order_id:
            seen_orders.add(key)
        partial_refund_rule = str(terms.get("refund_rule", "")).casefold()
        partial_refund_status = status in {"partially_refunded", "partially_refund", "partial_refund"}
        if status != "paid" and not (partial_refund_status and "reduce eligible amount by the refunded item amount" in partial_refund_rule):
            excluded.append({"platform": platform, "order_id": order_id, "reason": f"status is {status or 'missing'}, not paid"})
            continue

        currency = str(row.get("currency", "USD") or "").strip().upper()
        if not currency and not row.get("currency_column_present", "currency" in row):
            currency = "USD"
        if not currency:
            uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} has no currency")
            continue
        if row.get("data_conflicts"):
            uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} has conflicting exported fields: {', '.join(row['data_conflicts'])}")
            continue
        currencies.add(currency)
        if currency != "USD":
            uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} uses unsupported currency {currency}")
            continue

        if basis is None:
            uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'}: {basis_label}")
            continue
        if basis == "item_subtotal":
            subtotal = _money(row.get("item_subtotal"))
            discount = _money(row.get("discount"))
            if subtotal is None or discount is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing subtotal or discount data")
                continue
            amount = subtotal - discount
        else:
            amount = _money(row.get("order_total", row.get("amount")))
            if amount is None:
                excluded.append({"platform": platform, "order_id": order_id, "reason": "missing or invalid order total"})
                continue

        if terms.get("include_shipping") is True:
            shipping = _money(row.get("shipping"))
            if shipping is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing shipping data required by the terms")
                continue
            amount += shipping
        elif terms.get("include_shipping") is False and basis == "order_total":
            shipping = _money(row.get("shipping"))
            if shipping is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing shipping data required by the terms")
                continue
            amount -= shipping
        if terms.get("include_sales_tax") is True:
            tax = _money(row.get("sales_tax"))
            if tax is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing tax data required by the terms")
                continue
            amount += tax
        elif terms.get("include_sales_tax") is False and basis == "order_total":
            tax = _money(row.get("sales_tax"))
            if tax is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing tax data required by the terms")
                continue
            amount -= tax

        refund_rule = partial_refund_rule
        if "reduce eligible amount by the refunded item amount" in refund_rule:
            refunded = _money(row.get("item_refund"))
            if refunded is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing item refund data required by the terms")
                continue
            amount -= refunded
        elif refund_rule and not any(word in refund_rule for word in ("exclude", "reverse", "no refund")):
            uncertain_reasons.append(f"unsupported refund rule in written terms: {terms.get('refund_rule')}")
            continue

        if terms.get("deduct_platform_fees") is True:
            fees = _money(row.get("platform_fees"))
            if fees is None:
                uncertain_reasons.append(f"{platform} order {order_id or '(unknown)'} is missing platform fee data required by the terms")
                continue
            amount -= fees
        if amount > 0:
            paid.append({"platform": platform, "order_id": order_id, "amount": _number(_rounded(amount)), "currency": currency})
        else:
            excluded.append({"platform": platform, "order_id": order_id, "reason": "order total must be positive"})

    if len(currencies) > 1:
        uncertain_reasons.append("mixed currencies cannot be combined without an agreed conversion basis")
    if currencies - {"USD"}:
        # Keep unsupported-currency orders out of eligible counts and amounts.
        uncertain_reasons.append("commission currency must be USD unless an agreed conversion basis is provided")
    uncertain = bool(uncertain_reasons)
    gross_decimal = sum((Decimal(str(row["amount"])) for row in paid), Decimal("0"))
    gross = _rounded(gross_decimal)
    due = _rounded(gross * rate) if not uncertain else None
    return {
        "result": "uncertain — please check" if uncertain else ("match" if paid else f"no match found in imported sales as of {date.today().isoformat()}"),
        "eligible_sales": 0 if uncertain else len(paid), "eligible_orders": [] if uncertain else paid, "gross_sales": _number(gross),
        "commission_rate": _number(rate), "commission_due": _number(due),
        "excluded_orders": excluded,
        "uncertainty_reasons": sorted(set(uncertain_reasons)),
        "source": "owner-exported paid order records; verify against platform settlement records",
        "amount_basis": basis_label,
        "currency": "USD" if not currencies or currencies == {"USD"} else None,
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
    """Map Etsy or Shopify order export rows to one commission input per order."""
    # Keep aliases in precedence order. In particular, choose an explicit
    # order-total field before Etsy's item-only Order Value field.
    aliases = {
        "order_id": ("order id", "order", "name", "order number"),
        "status": ("order status", "financial status", "payment status", "status"),
        "order_total": ("order total", "total order value", "total", "order value"),
    }
    optional = {
        "item_subtotal": ("subtotal", "item subtotal", "order value"),
        "discount": ("discount amount", "discounts"),
        "shipping": ("shipping", "shipping amount"),
        "sales_tax": ("sales tax", "taxes", "tax"),
        "platform_fees": ("card processing fees", "adjusted card processing fees", "transaction fees"),
        "currency": ("currency",),
        "refunded": ("refunded amount", "refund amount"),
        "adjusted_order_total": ("adjusted order total",),
    }

    def field(row: dict[str, str], names: tuple[str, ...]) -> str | None:
        for name in names:
            if name in row and row[name].strip():
                return row[name].strip()
        return None

    def decimal_field(row: dict[str, str], names: tuple[str, ...]) -> Decimal | None:
        return _money(field(row, names))

    def details(row: dict[str, str]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for name, headers in optional.items():
            raw = field(row, headers)
            values[name] = raw if name == "currency" else _money(raw)
        total = decimal_field(row, aliases["order_total"])
        values["order_total"] = total
        values["amount"] = total
        # The export can include more than one explicit order-total column.
        # A precedence rule must not hide disagreement between those fields.
        total_candidates = {
            value for name in ("order total", "total order value", "total")
            if (value := decimal_field(row, (name,))) is not None
        }
        if len(total_candidates) > 1:
            values["data_conflicts"] = ["order total columns disagree"]
        # Etsy exports do not expose a dedicated refund amount in this layout.
        # Its adjusted total carries the net adjustment; treat only the
        # positive reduction as the refund candidate for an explicit refund rule.
        if values["refunded"] is None and platform.casefold() == "etsy":
            adjusted = values["adjusted_order_total"]
            if total is not None and adjusted is not None:
                values["refunded"] = max(Decimal("0"), total - adjusted)
        values["item_refund"] = values["refunded"]
        values["currency_column_present"] = "currency" in row
        return values

    result = []
    shopify_orders: dict[str, dict[str, Any]] = {}
    active_shopify_order = ""
    for row_number, original in enumerate(_read_csv(path), start=2):
        row = {_header_key(key): value for key, value in original.items() if key}
        mapped = {name: field(row, names) for name, names in aliases.items()}
        if mapped["order_id"] is None and platform.casefold() != "shopify":
            raise ValueError(f"{platform} CSV is missing a recognized order_id column")
        info = details(row)
        if platform.casefold() == "shopify":
            # Shopify's documented order CSV uses one line per line item and
            # leaves many order-level fields blank on continuation lines.
            # Preserve the order once, carrying forward the last order ID.
            order_id = mapped["order_id"] or active_shopify_order
            if order_id:
                active_shopify_order = order_id
            else:
                result.append({
                    "platform": platform, "order_id": "", "status": mapped["status"] or "",
                    **info, "source_row": row_number,
                })
                continue
            order = shopify_orders.setdefault(order_id, {
                "platform": platform, "order_id": order_id,
                "statuses": set(), "values": {key: set() for key in (*optional, "order_total")},
                "currency_column_present": False, "source_rows": [],
            })
            order["currency_column_present"] = order["currency_column_present"] or info["currency_column_present"]
            status = (mapped["status"] or "").strip().casefold()
            if status:
                order["statuses"].add(status)
            for key in order["values"]:
                value = info.get(key)
                if value not in (None, ""):
                    order["values"][key].add(value)
            order["source_rows"].append(row_number)
        else:
            result.append({
                "platform": platform, "order_id": mapped["order_id"] or "",
                "status": mapped["status"] or "", **info,
                "source_row": row_number,
            })
    for order in shopify_orders.values():
        statuses = order.pop("statuses")
        values = order.pop("values")
        order["status"] = next(iter(statuses)) if len(statuses) == 1 else (
            "conflicting status values" if statuses else ""
        )
        for key, candidates in values.items():
            if len(candidates) == 1:
                order[key] = next(iter(candidates))
            elif len(candidates) > 1:
                order[key] = None
                order.setdefault("data_conflicts", []).append(key)
            else:
                order[key] = None
        order["amount"] = order.get("order_total")
        order["item_refund"] = order.get("refunded")
        order["source_rows"] = order.pop("source_rows")
        result.append(order)
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
        terms = _read_json(args.rate_file) if args.rate_file else {"rate": args.rate}
        rate = args.rate if args.rate is not None else terms.get("rate")
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
        result = calculate_commissions(sales, rate, terms)
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
