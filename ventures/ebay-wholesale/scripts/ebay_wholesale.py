"""Prepare local eBay Sell API listing payloads and owner-reviewed supplier POs.

This module intentionally has no HTTP client. It creates reviewable files only;
the caller must use eBay's official APIs separately and the owner must approve
every external write, supplier purchase, and publication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote


REQUIRED_CATALOG_COLUMNS = {
    "sku", "supplier_sku", "title", "description", "category_id", "brand", "mpn",
    "condition", "quantity", "unit_cost", "shipping_cost", "supplier_lead_days",
    "image_urls", "aspects_json", "merchant_location_key", "supplier_name", "supplier_email",
}
CONDITIONS = {"NEW", "USED_EXCELLENT", "USED_VERY_GOOD", "USED_GOOD", "USED_ACCEPTABLE"}
MONEY = Decimal("0.01")


def _decimal(value: Any, label: str, *, minimum: Decimal | None = None) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValueError(f"{label} must be a decimal number") from None
    if not amount.is_finite() or (minimum is not None and amount < minimum):
        raise ValueError(f"{label} must be finite and at least {minimum}")
    return amount


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_CEILING))


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    number = _decimal(value, label, minimum=Decimal(minimum))
    if number != number.to_integral_value():
        raise ValueError(f"{label} must be a whole number")
    return int(number)


def _required(row: dict[str, str], key: str, row_number: int) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"row {row_number}: {key} is required")
    return value


def _handling_days(supplier_days: int, allowed_days: list[int]) -> int:
    valid = sorted({int(day) for day in allowed_days if int(day) >= 0})
    choices = [day for day in valid if day >= supplier_days]
    if not choices:
        raise ValueError(
            f"supplier_lead_days ({supplier_days}) exceeds the supplied eBay handling-time options"
        )
    return choices[0]


def _offer_price(row: dict[str, str], rules: dict[str, Any]) -> str:
    rate = _decimal(rules.get("fee_rate"), "fee_rate", minimum=Decimal(0))
    fixed_fee = _decimal(rules.get("fixed_fee"), "fixed_fee", minimum=Decimal(0))
    minimum_profit = _decimal(rules.get("minimum_profit_usd"), "minimum_profit_usd", minimum=Decimal(0))
    if rate >= 1:
        raise ValueError("fee_rate must be less than 1")
    landed_cost = _decimal(row["unit_cost"], "unit_cost", minimum=Decimal(0))
    landed_cost += _decimal(row["shipping_cost"], "shipping_cost", minimum=Decimal(0))
    denominator = Decimal(1) - rate
    return _money((landed_cost + fixed_fee + minimum_profit) / denominator)


def build_listing_drafts(
    csv_path: str | Path,
    *,
    pricing_rules: dict[str, Any],
    fulfillment_policy_ids: dict[str, str],
    allowed_handling_days: list[int],
    merchant_location_key: str = "OWNER_CONFIGURE_SHIP_FROM_LOCATION",
    marketplace_id: str = "EBAY_US",
    max_supplier_lead_days: int = 30,
) -> list[dict[str, Any]]:
    """Convert a supplier CSV to unpublished inventory/offer request bodies."""
    rows: list[dict[str, Any]] = []
    if not fulfillment_policy_ids:
        raise ValueError(f"no owner-configured fulfillment policy ID for {marketplace_id}")
    if not merchant_location_key.strip():
        raise ValueError("merchant_location_key is required")
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_CATALOG_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError("supplier catalog missing columns: " + ", ".join(sorted(missing)))
        seen: set[str] = set()
        for index, raw in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw.values()):
                continue
            row = {key: (value or "").strip() for key, value in raw.items()}
            sku = _required(row, "sku", index)
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", sku):
                raise ValueError(f"row {index}: sku must be 1-50 simple characters")
            if sku in seen:
                raise ValueError(f"row {index}: duplicate sku {sku}")
            seen.add(sku)
            title = _required(row, "title", index)
            description = _required(row, "description", index)
            category_id = _required(row, "category_id", index)
            quantity = _integer(row["quantity"], "quantity", minimum=1)
            supplier_days = _integer(row["supplier_lead_days"], "supplier_lead_days", minimum=0)
            if supplier_days > max_supplier_lead_days:
                raise ValueError(f"row {index}: supplier_lead_days exceeds configured limit")
            handling_days = _handling_days(supplier_days, allowed_handling_days)
            policy_id = (fulfillment_policy_ids.get(f"{marketplace_id}|{handling_days}") or "").strip()
            if not policy_id:
                raise ValueError(f"no fulfillment policy ID configured for {marketplace_id} with {handling_days}-day handling")
            condition_key = _required(row, "condition", index).upper()
            if condition_key not in CONDITIONS:
                raise ValueError(f"row {index}: condition must be an eBay condition value")
            images = [url.strip() for url in row["image_urls"].split(";") if url.strip()]
            if not images or any(not url.startswith("https://") for url in images):
                raise ValueError(f"row {index}: image_urls must contain https URLs separated by semicolons")
            try:
                aspects = json.loads(row["aspects_json"])
            except json.JSONDecodeError:
                raise ValueError(f"row {index}: aspects_json must be valid JSON") from None
            if not isinstance(aspects, dict) or not aspects:
                raise ValueError(f"row {index}: aspects_json must contain category-specific item specifics")
            for key in ("supplier_sku", "brand", "mpn", "supplier_name", "supplier_email"):
                _required(row, key, index)
            row_location = row.get("merchant_location_key") or merchant_location_key
            if not row_location:
                raise ValueError(f"row {index}: merchant_location_key is required")
            price = _offer_price(row, pricing_rules)
            item = {
                "availability": {"shipToLocationAvailability": {"quantity": quantity}},
                "condition": condition_key,
                "product": {
                    "title": title,
                    "description": description,
                    "brand": row["brand"],
                    "mpn": row["mpn"],
                    "imageUrls": images,
                    "aspects": aspects,
                },
            }
            offer = {
                "sku": sku,
                "marketplaceId": marketplace_id,
                "format": "FIXED_PRICE",
                "availableQuantity": quantity,
                "categoryId": category_id,
                "merchantLocationKey": row_location,
                "listingDescription": description,
                "listingPolicies": {
                    "fulfillmentPolicyId": policy_id,
                    "paymentPolicyId": "OWNER_CONFIGURE_PAYMENT_POLICY",
                    "returnPolicyId": "OWNER_CONFIGURE_RETURN_POLICY",
                },
                "pricingSummary": {"price": {"value": price, "currency": "USD"}},
            }
            rows.append({
                "sku": sku,
                "supplier": {"name": row["supplier_name"], "email": row["supplier_email"],
                              "sku": row["supplier_sku"]},
                "supplier_lead_days": supplier_days,
                "handling_time_days": handling_days,
                "fulfillment_policy_draft": {"handlingTime": {"unit": "DAY", "value": str(handling_days)}},
                "inventory_item_method": "PUT",
                "inventory_item_path": f"/sell/inventory/v1/inventory_item/{quote(sku, safe='')}",
                "inventory_item": item,
                "offer_path": "/sell/inventory/v1/offer",
                "offer": offer,
                "price_inputs": {
                    "supplier_unit_cost_usd": row["unit_cost"],
                    "supplier_shipping_cost_usd": row["shipping_cost"],
                    "fee_rate_source": "owner-configured current eBay fee schedule",
                    "minimum_profit_usd": str(pricing_rules["minimum_profit_usd"]),
                },
                "owner_review_required": True,
                "publish_allowed": False,
            })
    if not rows:
        raise ValueError("supplier catalog has no product rows")
    return rows


def build_supplier_po(order: dict[str, Any], *, supplier_by_sku: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Create a local PO draft from a Fulfillment API getOrder response."""
    order_id = str(order.get("orderId") or "").strip()
    line_items = order.get("lineItems")
    instructions = order.get("fulfillmentStartInstructions") or []
    ship_to = (instructions[0].get("shippingStep") or {}).get("shipTo") if instructions else None
    address = (ship_to or {}).get("contactAddress") if isinstance(ship_to, dict) else None
    if not order_id or not isinstance(line_items, list) or not line_items:
        raise ValueError("orderId and at least one line item are required")
    if not isinstance(address, dict) or not address.get("postalCode") or not address.get("countryCode"):
        raise ValueError("eBay order has no usable ship-to address")
    items = []
    supplier: dict[str, str] | None = None
    for line in line_items:
        sku = str(line.get("sku") or "").strip()
        mapping = supplier_by_sku.get(sku)
        if not mapping:
            raise ValueError(f"supplier mapping missing for eBay SKU {sku or '(blank)'}")
        if supplier and supplier.get("name") != mapping.get("name"):
            raise ValueError("one PO draft can contain items for only one supplier")
        supplier = mapping
        quantity = _integer(line.get("quantity"), "order quantity", minimum=1)
        items.append({"sku": mapping.get("sku", sku), "quantity": quantity})
    buyer_name = str(ship_to.get("fullName") or "").strip()
    return {
        "status": "DRAFT_FOR_OWNER_APPROVAL",
        "approval_required": True,
        "send_allowed": False,
        "order_id": order_id,
        "supplier": {"name": supplier["name"], "email": supplier.get("email", "")},
        "ship_to": {"name": buyer_name, **address},
        "items": items,
        "notes": "Verify address, availability, agreed wholesale price, freight, promised dispatch, and eBay ship-by date before approving. No PO sent.",
    }


def fulfillment_order_get_request(order_id: str) -> dict[str, str]:
    """Describe the official, read-only Sell Fulfillment API order lookup."""
    order_id = str(order_id or "").strip()
    if not order_id or any(char in order_id for char in "\r\n"):
        raise ValueError("order_id is required")
    return {
        "method": "GET",
        "path": f"/sell/fulfillment/v1/order/{quote(order_id, safe='!')}",
        "side_effect": "none",
    }


class EbaySellApi:
    """Small official REST adapter; every write requires explicit owner approval."""

    HOSTS = {
        "production": "https://api.ebay.com",
        "sandbox": "https://api.sandbox.ebay.com",
    }

    def __init__(self, access_token: str, *, environment: str = "sandbox",
                 transport: Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]] | None = None,
                 audit_writer: Callable[[dict[str, Any]], None] | None = None):
        if environment not in self.HOSTS:
            raise ValueError("environment must be sandbox or production")
        if not access_token.strip():
            raise ValueError("an eBay OAuth user access token is required")
        self.base_url = self.HOSTS[environment]
        self.access_token = access_token
        self.transport = transport or self._urlopen_transport
        self.audit_writer = audit_writer

    @staticmethod
    def _urlopen_transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()
        except URLError as exc:
            raise RuntimeError(f"eBay API connection failed: {exc.reason}") from exc

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US",
            "Accept": "application/json",
        }
        raw = json.dumps(body).encode("utf-8") if body is not None else None
        status, response = self.transport(method, self.base_url + path, headers, raw)
        if status < 200 or status >= 300:
            raise RuntimeError(f"eBay API returned HTTP {status}: {response.decode('utf-8', errors='replace')[:500]}")
        return json.loads(response) if response else {"http_status": status}

    def get_order(self, order_id: str) -> dict[str, Any]:
        """Read an order through the official Fulfillment API."""
        request = fulfillment_order_get_request(order_id)
        return self._call(request["method"], request["path"])

    def create_inventory_location(self, location_key: str, payload: dict[str, Any], *, owner_approved: bool) -> dict[str, Any]:
        if not owner_approved:
            raise PermissionError("owner approval is required for an eBay inventory location write")
        address = payload.get("location", {}).get("address", {})
        if not payload.get("name") or not (address.get("postalCode") and address.get("country")):
            raise ValueError("inventory location payload needs a name, postal code, and country")
        self._reject_placeholders(payload)
        return self._audited_write("POST", f"/sell/inventory/v1/location/{quote(location_key, safe='')}", payload)

    def create_or_replace_inventory_item(self, sku: str, payload: dict[str, Any], *, owner_approved: bool) -> dict[str, Any]:
        if not owner_approved:
            raise PermissionError("owner approval is required for an eBay inventory write")
        if (not payload.get("product", {}).get("title") or not payload.get("condition")
                or not payload.get("availability", {}).get("shipToLocationAvailability", {}).get("quantity")):
            raise ValueError("inventory item payload is incomplete")
        self._reject_placeholders(payload)
        return self._audited_write("PUT", f"/sell/inventory/v1/inventory_item/{quote(sku, safe='')}", payload)

    def create_offer(self, payload: dict[str, Any], *, owner_approved: bool) -> dict[str, Any]:
        if not owner_approved:
            raise PermissionError("owner approval is required for an eBay offer write")
        policies = payload.get("listingPolicies", {})
        required = ("sku", "marketplaceId", "format", "availableQuantity", "categoryId",
                    "merchantLocationKey", "listingDescription", "pricingSummary")
        if any(not payload.get(field) for field in required) or any(not policies.get(field) for field in (
                "fulfillmentPolicyId", "paymentPolicyId", "returnPolicyId")):
            raise ValueError("offer payload is incomplete")
        self._reject_placeholders(payload)
        return self._audited_write("POST", "/sell/inventory/v1/offer", payload)

    def publish_offer(self, offer_id: str, *, owner_approved: bool) -> dict[str, Any]:
        if not owner_approved:
            raise PermissionError("separate owner approval is required before publishing an eBay listing")
        return self._audited_write("POST", f"/sell/inventory/v1/offer/{quote(offer_id, safe='')}/publish")

    def _audited_write(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.audit_writer is None:
            raise PermissionError("a Glacier audit-event writer is required before any eBay API write")
        raw = json.dumps(body, sort_keys=True).encode("utf-8") if body is not None else b""
        event = {
            "source": "ebay-wholesale",
            "action": "ebay_api_write",
            "method": method,
            "path": path,
            "request_sha256": hashlib.sha256(raw).hexdigest(),
            "stage": "approved_request",
        }
        # The event must be durably accepted before the outbound write begins.
        self.audit_writer(event)
        try:
            result = self._call(method, path, body)
        except Exception as exc:
            self.audit_writer({**event, "stage": "failed", "error_type": type(exc).__name__})
            raise
        self.audit_writer({
            **event,
            "stage": "completed",
            "response_sha256": hashlib.sha256(json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest(),
        })
        return result

    @staticmethod
    def _reject_placeholders(payload: dict[str, Any]) -> None:
        def visit(value: Any) -> bool:
            if isinstance(value, str):
                return "OWNER_CONFIGURE" in value or "TO_BE_CONFIGURED" in value
            if isinstance(value, dict):
                return any(visit(child) for child in value.values())
            if isinstance(value, list):
                return any(visit(child) for child in value)
            return False

        if visit(payload):
            raise ValueError("API payload contains an unconfigured owner placeholder")


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare local eBay listing and supplier PO drafts")
    commands = parser.add_subparsers(dest="command", required=True)
    listings = commands.add_parser("listings")
    listings.add_argument("--catalog", required=True)
    listings.add_argument("--rules", required=True, help="owner-configured fee and minimum-profit JSON")
    listings.add_argument("--policies", required=True, help="owner-configured marketplace fulfillment policy IDs")
    listings.add_argument("--location-key", required=True)
    listings.add_argument("--allowed-handling-days", required=True, help="comma-separated values from eBay metadata")
    listings.add_argument("--output", required=True)
    po = commands.add_parser("po")
    po.add_argument("--order", required=True, help="owner-exported or official Fulfillment API order JSON")
    po.add_argument("--supplier-map", required=True)
    po.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "listings":
            rows = build_listing_drafts(
                args.catalog,
                pricing_rules=json.loads(Path(args.rules).read_text(encoding="utf-8")),
                fulfillment_policy_ids=json.loads(Path(args.policies).read_text(encoding="utf-8")),
                merchant_location_key=args.location_key,
                allowed_handling_days=[int(x) for x in args.allowed_handling_days.split(",")],
            )
            _write_json(args.output, {"drafts": rows, "external_writes_performed": False})
        else:
            _write_json(args.output, build_supplier_po(
                json.loads(Path(args.order).read_text(encoding="utf-8")),
                supplier_by_sku=json.loads(Path(args.supplier_map).read_text(encoding="utf-8")),
            ))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
