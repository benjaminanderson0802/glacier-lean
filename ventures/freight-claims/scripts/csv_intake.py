"""Parse ShipStation shipment and order CSV exports into shipment records."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _columns(headers: list[str]) -> dict[str, str]:
    aliases = {
        "order": ("ordernumber", "ordernum", "order", "orderno", "orderid", "order"),
        "shipment": ("shipmentid", "shipmentnumber"),
        "ship_date": ("shipdate", "date shipped", "shipdateutc"),
        "carrier": ("carrier", "carriername", "carrier code"),
        "service": ("service", "shippingservice", "servicecode"),
        "tracking": ("trackingnumber", "tracking", "trackingnum"),
        "recipient": ("recipient", "shiptoname", "recipientname"),
        "address1": ("shiptoaddress", "shiptoaddress1", "address1", "shipto"),
        "address2": ("shiptoaddress2", "address2"),
        "city": ("shiptocity", "city"),
        "state": ("shiptostate", "state", "province"),
        "postal": ("shiptopostalcode", "shiptozip", "postalcode", "zipcode", "zip"),
        "country": ("shiptocountry", "country"),
        "weight": ("weight", "weightlb", "weightlbs", "weightoz", "shipmentweight"),
        "shipping_cost": ("shippingcost", "shippingamount", "shipcost"),
        "order_total": ("ordertotal", "total", "ordertotalamount"),
        "items": ("itemssku", "items", "sku", "productsku"),
        "status": ("status", "shipmentstatus", "trackingstatus", "orderstatus"),
    }
    normalized = {_key(header): header for header in headers}
    result = {}
    for field, candidates in aliases.items():
        for candidate in candidates:
            header = normalized.get(_key(candidate))
            if header is not None:
                result[field] = header
                break
    return result


def _value(row: dict[str, str], columns: dict[str, str], field: str) -> str:
    value = row.get(columns.get(field, ""), "")
    return value.strip() if isinstance(value, str) else ""


def _weight(value: str) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", value.replace(",", ""))
    if not match:
        return None
    try:
        result = float(match.group())
    except ValueError:
        return None
    return result if result >= 0 else None


def _items(value: str) -> list[dict[str, Any]]:
    """Read common display strings such as ``Widget / SKU-1 x2`` without guessing prices."""
    if not value:
        return []
    parsed = []
    for part in re.split(r"\s*[;|]\s*", value):
        part = part.strip()
        if not part:
            continue
        quantity = 1
        quantity_match = re.search(r"\s+x\s*(\d+)\s*$", part, re.I)
        if quantity_match:
            quantity = int(quantity_match.group(1))
            part = part[:quantity_match.start()].strip()
        if " / " in part:
            name, sku = (piece.strip() for piece in part.rsplit(" / ", 1))
        else:
            name, sku = part, part
        parsed.append({"sku": sku, "name": name, "quantity": quantity})
    return parsed


def parse_shipments_csv(path: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return normalized ShipStation rows and row-numbered skip reasons."""
    source = Path(path).expanduser()
    shipments: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        columns = _columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                continue
            tracking = _value(row, columns, "tracking")
            if not tracking:
                skipped.append({"row": row_number, "reason": "missing tracking number"})
                continue
            order = _value(row, columns, "order")
            shipment_id = _value(row, columns, "shipment") or (f"SS-ORD-{order}" if order else tracking)
            status = _value(row, columns, "status")
            carrier = _value(row, columns, "carrier")
            ship_to = {
                "name": _value(row, columns, "recipient"),
                "address_line1": _value(row, columns, "address1"),
                "city": _value(row, columns, "city"),
                "state": _value(row, columns, "state"),
                "postal_code": _value(row, columns, "postal"),
                "country": _value(row, columns, "country"),
            }
            address2 = _value(row, columns, "address2")
            if address2:
                ship_to["address_line2"] = address2
            item_rows = _items(_value(row, columns, "items"))
            weight_header = columns.get("weight", "").casefold()
            weight_lb = _weight(_value(row, columns, "weight"))
            if weight_lb is not None and ("ounce" in weight_header or "(oz" in weight_header or weight_header.endswith("oz)")):
                weight_lb = round(weight_lb / 16, 4)
            record: dict[str, Any] = {
                "shipment_id": shipment_id,
                "order_number": order,
                "carrier": carrier,
                "carrier_code": re.sub(r"[^a-z0-9]+", "_", carrier.casefold()).strip("_"),
                "service": _value(row, columns, "service"),
                "tracking_number": tracking,
                "ship_date": _value(row, columns, "ship_date"),
                "ship_to": ship_to,
                "weight_lb": weight_lb,
                "shipping_cost": _value(row, columns, "shipping_cost"),
                "order_total": _value(row, columns, "order_total"),
                "items": item_rows,
                "shipment_status": status,
                "tracking_status": status,
                "labels": [],
            }
            shipments.append(record)
    return shipments, skipped
