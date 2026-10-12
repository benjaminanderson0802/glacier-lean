"""Local-only buy-first resale listing prep and sold-item checklist."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
import re


INPUT_FIELDS = (
    "item_id", "inventory_source", "category", "brand", "item_type", "style_terms", "color", "size",
    "condition", "flaws", "measurements", "expected_sale_usd", "acquisition_cost_usd",
    "shipping_paid_by_seller_usd", "packaging_cost_usd", "photo_paths", "photo_origin",
)
HANDOFF_FIELDS = (
    "item_id", "title", "description", "tags", "size", "condition", "price_usd",
    "category", "brand", "photo_paths",
)
CONDITION_VALUES = {"Good", "Satisfactory"}
USED_SOURCE_VALUES = {"thrift_store", "used_clothing_lot", "consignment", "private_seller"}

# Trend-led sourcing shortlist, not a sales ranking or a promise of demand.
CATEGORIES = [
    {"rank": 1, "category": "vintage denim and workwear", "expected_sale_usd": 42.00,
     "max_buy_usd": 18.16, "evidence": "Depop September 2026 trend article calls vintage denim in-demand; 2026 report notes workwear search spikes."},
    {"rank": 2, "category": "sports jerseys and athletic staples", "expected_sale_usd": 35.00,
     "max_buy_usd": 14.90, "evidence": "Depop 2026 trend report cites spikes for vintage Lululemon and upcycled jerseys; June 2026 trend article covers jerseys and gym sets."},
    {"rank": 3, "category": "collegiate and preppy used clothing", "expected_sale_usd": 38.00,
     "max_buy_usd": 16.30, "evidence": "Depop August 2026 article cites growing demand for vintage rugby shirts, varsity jackets, embroidered polos, and striped knits."},
    {"rank": 4, "category": "occasion dresses and skirts", "expected_sale_usd": 34.00,
     "max_buy_usd": 14.43, "evidence": "Depop 2026 trend report cites search gains for bandage dresses and draped skirts; June 2026 trend article highlights vintage dresses."},
    {"rank": 5, "category": "band tees and alternative tops", "expected_sale_usd": 30.00,
     "max_buy_usd": 12.56, "evidence": "Depop's 2025 report identifies band tees, knee-high boots, and faux fur in its Indie Vanguard trend."},
]


def category_research() -> list[dict]:
    """Return the five source-backed categories and illustrative per-piece ceilings."""
    return [dict(row) for row in CATEGORIES]


def max_buy_price(
    *, expected_sale: float, target_margin: float, processing_rate: float,
    processing_flat: float, seller_shipping: float, packaging: float,
) -> float:
    """Maximum landed item cost for the selected contribution margin.

    Margin is after payment processing, seller-paid postage, and packaging, before
    owner labor, taxes, returns, boosting, and other overhead.
    """
    if expected_sale <= 0 or not 0 <= target_margin < 1 or not 0 <= processing_rate < 1:
        raise ValueError("sale price must be positive and rates must be within range")
    ceiling = expected_sale * (1 - target_margin - processing_rate) - processing_flat - seller_shipping - packaging
    return round(max(0.0, ceiling) + 1e-9, 2)


def read_inventory(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(set(INPUT_FIELDS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"input is missing required fields: {', '.join(missing)}")
        rows = []
        for line, raw in enumerate(reader, start=2):
            row = {field: (raw.get(field) or "").strip() for field in INPUT_FIELDS}
            if not row["item_id"]:
                raise ValueError(f"row {line} needs an item_id")
            for field in ("expected_sale_usd", "acquisition_cost_usd", "shipping_paid_by_seller_usd", "packaging_cost_usd"):
                try:
                    number = float(row[field])
                except ValueError as exc:
                    raise ValueError(f"row {line} has an invalid {field}") from exc
                if number < 0:
                    raise ValueError(f"row {line} has a negative {field}")
            if not row["category"]:
                raise ValueError(f"row {line} needs a category")
            if row["inventory_source"] not in USED_SOURCE_VALUES:
                raise ValueError(
                    f"row {line} inventory_source must be one of: {', '.join(sorted(USED_SOURCE_VALUES))}"
                )
            rows.append(row)
    return rows


def _item_tags(row: dict[str, str]) -> str:
    candidates = [row["style_terms"], row["category"], row["item_type"], row["color"]]
    tags: list[str] = []
    for candidate in candidates:
        for term in re.split(r"[,|;]", candidate.casefold()):
            normalized = " ".join(term.split())
            if normalized and normalized not in tags:
                tags.append(normalized)
    return "|".join(tags[:5])


def prepare_listings(rows: list[dict[str, str]], *, photo_root: str | Path) -> list[dict[str, str]]:
    photo_root = Path(photo_root).resolve()
    prepared = []
    seen_ids: set[str] = set()
    for row in rows:
        if row["item_id"] in seen_ids:
            raise ValueError(f"duplicate item_id: {row['item_id']}")
        seen_ids.add(row["item_id"])
        if row["photo_origin"] != "owner_original":
            raise ValueError(f"{row['item_id']} photo_origin must be owner_original")
        if row["inventory_source"] not in USED_SOURCE_VALUES:
            raise ValueError(f"{row['item_id']} must be bought as used inventory from an allowed source")
        photos = [part.strip() for part in row["photo_paths"].split("|") if part.strip()]
        if not photos:
            raise ValueError(f"{row['item_id']} needs at least one owner photo")
        for photo in photos:
            path = (photo_root / photo).resolve()
            if photo_root not in path.parents or not path.is_file():
                raise ValueError(f"{row['item_id']} photo path is missing or outside the photo folder: {photo}")
        if row["condition"] not in CONDITION_VALUES:
            raise ValueError(f"{row['item_id']} condition must be one of: {', '.join(sorted(CONDITION_VALUES))}")
        required = ("item_type", "color", "size", "expected_sale_usd")
        missing = [field for field in required if not row[field]]
        if missing:
            raise ValueError(f"{row['item_id']} missing listing facts: {', '.join(missing)}")

        title_parts = [row["style_terms"], row["item_type"], row["color"], row["size"]]
        title = " ".join(" ".join(part.split()).title() for part in title_parts if part)
        title = title[:65].rstrip()
        description_parts = [f"{row['condition']} condition."]
        if row["flaws"]:
            description_parts.append(f"Details: {row['flaws']}.")
        if row["measurements"]:
            description_parts.append(f"Measurements: {row['measurements']}.")
        description_parts.append("See the original item photos for color, labels, and visible details.")
        prepared.append({
            "item_id": row["item_id"], "title": title,
            "description": " ".join(description_parts), "tags": _item_tags(row),
            "size": row["size"], "condition": row["condition"],
            "price_usd": f"{float(row['expected_sale_usd']):.2f}",
            "category": row["category"], "brand": row["brand"] or "uncertain - please check",
            "photo_paths": "|".join(photos),
        })
    return prepared


def write_handoff_csv(rows: list[dict[str, str]], path: str | Path) -> None:
    """Write a local, vendor-neutral CSV handoff. Never opens a marketplace."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HANDOFF_FIELDS)
        writer.writeheader()
        writer.writerows([{field: row[field] for field in HANDOFF_FIELDS} for row in rows])


def shipping_checklist(*, item_id: str, buyer_name: str, sold_at: str, carrier: str, label_reference: str) -> dict:
    if not item_id.strip() or not buyer_name.strip():
        raise ValueError("item_id and buyer_name are required")
    date.fromisoformat(sold_at)
    return {
        "item_id": item_id.strip(), "buyer_name": buyer_name.strip(), "sold_at": sold_at,
        "carrier": carrier.strip() or "uncertain - please check", "label_reference": label_reference.strip() or "owner to add after purchase",
    }


def render_shipping_checklist(item: dict) -> str:
    return "\n".join([
        f"# Sold item shipping checklist — {item['item_id']}", "",
        f"Sold: {item['sold_at']} | Buyer: {item['buyer_name']}", "",
        "- [ ] Confirm sold order in Depop and verify the item ID, ship-to address, dispatch deadline, and selected shipping method.",
        "- [ ] Match the item ID to the physical inventory; check condition and remove it from any other marketplace promptly if it sold there too.",
        "- [ ] Choose the correct parcel size and packaging; weigh and measure the packed item.",
        "- [ ] Buy or generate the shipping label yourself; this checklist does not purchase a label. If you selected Depop Shipping, use the Depop-generated label only. If you selected Other, arrange tracked shipping yourself and enter tracking carefully.",
        f"- [ ] Carrier: {item['carrier']} | Label/tracking reference: {item['label_reference']}",
        "- [ ] Pack the item securely, include any packing slip needed, and photograph the sealed parcel for your own records.",
        "- [ ] Hand the parcel to the carrier, keep proof of acceptance/tracking, and meet the order's dispatch deadline.",
        "- [ ] Mark as shipped in Depop or confirm tracking is present, according to the shipping method you selected.",
        "",
        "Owner action only: confirm the live order and address, purchase the label, pack, and dispatch. Do not place personal data or buyer addresses in public files.",
        "",
    ])


def write_shipping_checklist(item: dict, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_shipping_checklist(item), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare local resale listing drafts and sold-item checklists; no marketplace access.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing_parser = subparsers.add_parser("listings")
    listing_parser.add_argument("--input", required=True)
    listing_parser.add_argument("--photo-root", required=True)
    listing_parser.add_argument("--output", required=True)
    ship_parser = subparsers.add_parser("shipping")
    ship_parser.add_argument("--item-id", required=True)
    ship_parser.add_argument("--buyer-name", required=True)
    ship_parser.add_argument("--sold-at", required=True)
    ship_parser.add_argument("--carrier", default="")
    ship_parser.add_argument("--label-reference", default="")
    ship_parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "listings":
            rows = prepare_listings(read_inventory(args.input), photo_root=args.photo_root)
            write_handoff_csv(rows, args.output)
        else:
            item = shipping_checklist(item_id=args.item_id, buyer_name=args.buyer_name,
                                      sold_at=args.sold_at, carrier=args.carrier,
                                      label_reference=args.label_reference)
            write_shipping_checklist(item, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
