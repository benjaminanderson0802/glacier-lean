from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
VENTURE = ROOT / "ventures" / "ebay-wholesale"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(VENTURE))

from scripts.ebay_wholesale import (  # noqa: E402
    build_listing_drafts,
    build_supplier_po,
    fulfillment_order_get_request,
    EbaySellApi,
)


def test_manifest_is_valid_and_exactly_one_prelaunch_step():
    schema = json.loads((ROOT / "ventures" / "venture.schema.json").read_text())
    manifest = json.loads((VENTURE / "venture.json").read_text())
    jsonschema.validate(manifest, schema)
    assert len(manifest["your_steps"]) == 1


def test_csv_creates_local_inventory_and_offer_drafts_with_safe_price_and_lead_time(tmp_path):
    csv_path = VENTURE / "tests" / "fixtures" / "supplier-catalog.csv"
    rules = {"fee_rate": "0.13", "fixed_fee": "0.30", "minimum_profit_usd": "0.00"}

    result = build_listing_drafts(
        csv_path,
        pricing_rules=rules,
        fulfillment_policy_ids={"EBAY_US|10": "policy-fixture-1"},
        allowed_handling_days=[1, 2, 3, 4, 5, 10, 15, 20],
    )

    assert len(result) == 1
    row = result[0]
    assert row["inventory_item_path"] == "/sell/inventory/v1/inventory_item/VOL-ATS-100"
    assert row["inventory_item"]["product"]["title"] == "Commercial transfer switch"
    assert row["offer_path"] == "/sell/inventory/v1/offer"
    assert row["offer"]["listingPolicies"]["fulfillmentPolicyId"] == "policy-fixture-1"
    assert row["offer"]["merchantLocationKey"] == "supplier-warehouse-fixture"
    # $575 landed + $0.30 + 13% fee => next cent ceiling to break even.
    assert row["offer"]["pricingSummary"]["price"]["value"] == "661.27"
    assert row["fulfillment_policy_draft"]["handlingTime"] == {"unit": "DAY", "value": "10"}
    assert row["publish_allowed"] is False
    assert row["owner_review_required"] is True


def test_csv_refuses_unknown_costs_or_lead_time_beyond_marketplace_options(tmp_path):
    catalog = VENTURE / "tests" / "fixtures" / "supplier-catalog-missing-lead.csv"
    with pytest.raises(ValueError, match="supplier_lead_days"):
        build_listing_drafts(
            catalog,
            pricing_rules={"fee_rate": "0.13", "fixed_fee": "0.30", "minimum_profit_usd": "0"},
            fulfillment_policy_ids={"EBAY_US|10": "fixture-policy"},
            allowed_handling_days=[1, 2, 3, 4, 5, 10, 15, 20],
            max_supplier_lead_days=30,
        )


def test_order_fixture_prepares_supplier_po_but_never_sends_it():
    order = json.loads((VENTURE / "tests" / "fixtures" / "fulfillment-order.json").read_text())
    po = build_supplier_po(order, supplier_by_sku={"VOL-ATS-100": {
        "name": "Fixture Supply", "email": "orders@supplier.example", "sku": "ATS-100"
    }})

    assert po["order_id"] == "12-34567-89012"
    assert po["ship_to"]["postalCode"] == "30303"
    assert po["items"] == [{"sku": "ATS-100", "quantity": 1}]
    assert po["status"] == "DRAFT_FOR_OWNER_APPROVAL"
    assert po["approval_required"] is True
    assert po["send_allowed"] is False


def test_order_without_supplier_mapping_or_buyer_address_is_not_forwardable():
    order = json.loads((VENTURE / "tests" / "fixtures" / "fulfillment-order.json").read_text())
    with pytest.raises(ValueError, match="supplier mapping"):
        build_supplier_po(order, supplier_by_sku={})
    order["fulfillmentStartInstructions"][0]["shippingStep"].pop("shipTo")
    with pytest.raises(ValueError, match="ship-to"):
        build_supplier_po(order, supplier_by_sku={"VOL-ATS-100": {
            "name": "Fixture Supply", "email": "orders@supplier.example", "sku": "ATS-100"
        }})


def test_fulfillment_order_lookup_is_official_get_request_only():
    assert fulfillment_order_get_request("12-34567-89012") == {
        "method": "GET", "path": "/sell/fulfillment/v1/order/12-34567-89012", "side_effect": "none"
    }


def test_official_sell_api_adapter_uses_fixture_transport_and_requires_approval_for_writes():
    calls = []

    def fake_transport(method, url, headers, body):
        calls.append((method, url, headers, body))
        if method == "GET":
            return 200, (VENTURE / "tests" / "fixtures" / "fulfillment-order.json").read_bytes()
        if url.endswith("/publish"):
            return 200, b'{"listingId":"listing-fixture"}'
        if url.endswith("/offer"):
            return 201, b'{"offerId":"offer-fixture"}'
        return 204, b""

    audit_events = []
    api = EbaySellApi("fixture-token", environment="sandbox", transport=fake_transport, audit_writer=audit_events.append)
    order = api.get_order("12-34567-89012")
    assert order["orderId"] == "12-34567-89012"
    location_payload = {
        "location": {"address": {"postalCode": "30303", "country": "US"}},
        "name": "Supplier warehouse fixture", "merchantLocationStatus": "ENABLED", "locationTypes": ["WAREHOUSE"],
    }
    with pytest.raises(PermissionError, match="owner approval"):
        api.create_inventory_location("supplier-warehouse-fixture", location_payload, owner_approved=False)
    api.create_inventory_location("supplier-warehouse-fixture", location_payload, owner_approved=True)
    assert calls[-1][0] == "POST" and calls[-1][1].endswith("/location/supplier-warehouse-fixture")
    with pytest.raises(PermissionError, match="owner approval"):
        api.create_or_replace_inventory_item("VOL-ATS-100", {"condition": "NEW"}, owner_approved=False)
    item_payload = {
        "availability": {"shipToLocationAvailability": {"quantity": 3}},
        "condition": "NEW",
        "product": {"title": "Commercial transfer switch", "description": "Fixture item"},
    }
    api.create_or_replace_inventory_item("VOL-ATS-100", item_payload, owner_approved=True)
    assert calls[-1][0] == "PUT"
    assert calls[-1][1] == "https://api.sandbox.ebay.com/sell/inventory/v1/inventory_item/VOL-ATS-100"
    assert calls[-1][2]["Authorization"] == "Bearer fixture-token"
    offer_payload = {
        "sku": "VOL-ATS-100", "marketplaceId": "EBAY_US", "format": "FIXED_PRICE",
        "availableQuantity": 3, "categoryId": "26221", "merchantLocationKey": "seller-location",
        "listingDescription": "Fixture item", "pricingSummary": {"price": {"value": "661.27", "currency": "USD"}},
        "listingPolicies": {"fulfillmentPolicyId": "fulfillment-1", "paymentPolicyId": "payment-1",
                             "returnPolicyId": "return-1"},
    }
    offer = api.create_offer(offer_payload, owner_approved=True)
    assert offer["offerId"] == "offer-fixture"
    with pytest.raises(PermissionError, match="separate owner approval"):
        api.publish_offer("offer-fixture", owner_approved=False)
    assert api.publish_offer("offer-fixture", owner_approved=True)["listingId"] == "listing-fixture"
    assert calls[-1][0] == "POST" and calls[-1][1].endswith("/offer/offer-fixture/publish")
    with pytest.raises(ValueError, match="placeholder"):
        api.create_offer({**offer_payload, "merchantLocationKey": "OWNER_CONFIGURE_LOCATION"}, owner_approved=True)
    assert [event["stage"] for event in audit_events] == [
        "approved_request", "completed", "approved_request", "completed",
        "approved_request", "completed", "approved_request", "completed",
    ]
    assert all(event["action"] == "ebay_api_write" and event["request_sha256"] for event in audit_events)

    no_audit_api = EbaySellApi("fixture-token", environment="sandbox", transport=fake_transport)
    prior_calls = len(calls)
    with pytest.raises(PermissionError, match="audit-event writer"):
        no_audit_api.create_offer(offer_payload, owner_approved=True)
    assert len(calls) == prior_calls
