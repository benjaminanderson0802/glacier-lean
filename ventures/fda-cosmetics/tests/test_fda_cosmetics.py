from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "listing_prep.py"
SPEC = importlib.util.spec_from_file_location("fda_listing_prep", MODULE_PATH)
listing_prep = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(listing_prep)


FDA = "https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing"


def listing_payload(label_path: Path, **updates):
    payload = {
        "responsible_person_name": "Example Beauty LLC",
        "responsible_person_phone": "+1-555-0101",
        "responsible_person_role": "manufacturer",
        "product_category_codes": ["06A2"],
        "product_name": "Daily Conditioner",
        "fragrance_or_flavor": ["fragrance"],
        "facility_fei": ["1234567890"],
        "facility_exempt": False,
        "facilities": [{"fei": "1234567890", "exempt_confirmed": False}],
        "ingredients": ["Water", "Glycerin", "Fragrance"],
        "ingredient_document": str(label_path),
        "exemption_checklist": {"small_business": False, "product_may_be_covered_exception": False, "customer_wants_listing": True},
        "customer_confirmed": True,
        "source": "owner-upload",
        "as_of": "2026-10-10",
    }
    payload.update(updates)
    return payload


def test_valid_customer_confirmed_listing_builds_customer_submit_zip(tmp_path, monkeypatch):
    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture; reader is mocked below")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    result = listing_prep.prepare_listing(listing_payload(label), tmp_path, as_of="2026-10-10")

    assert result["result"] == "match"
    assert result["customer_must_submit"] is True
    assert result["submitted"] is False
    assert result["signed"] is False
    assert result["spl_zip"]
    with zipfile.ZipFile(tmp_path / result["spl_zip"]) as archive:
        assert archive.namelist() == [result["spl_xml"]]
        xml = ET.fromstring(archive.read(result["spl_xml"]))
        ns = {"s": "urn:hl7-org:v3"}
        assert xml.find("s:code", ns).attrib["code"] == "103572-4"
        assert xml.find(".//s:author/s:assignedEntity/s:representedOrganization/s:name", ns).text == "Example Beauty LLC"
        assert [node.text for node in xml.findall(".//s:ingredient/s:ingredientSubstance/s:name", ns)] == ["Water", "Glycerin", "Fragrance"]
        assert xml.find("s:legalAuthenticator", ns) is None
    assert result["rules"]["verdict"] == "pass"
    assert all(row["cite"] for row in result["rules"]["results"])
    assert result["sources"]["fda_form"] == FDA


def test_unconfirmed_or_reader_uncertain_ingredients_stop_spl_generation(tmp_path, monkeypatch):
    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture; reader is mocked below")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {
        "fields": {"ingredients": {"value": "Water, Glycerin", "page": 1, "confidence": 0.51, "uncertain": True}},
        "text": "Ingredients: Water, Glycerin",
    })
    result = listing_prep.prepare_listing(
        listing_payload(label, customer_confirmed=False),
        tmp_path,
        as_of="2026-10-10",
    )

    assert result["result"] == "uncertain — please check"
    assert result["spl_zip"] is None
    assert "ingredients" in result["please_confirm"]
    assert not list(tmp_path.glob("*.zip"))


def test_unreadable_label_stays_uncertain_instead_of_crashing(tmp_path):
    label = tmp_path / "corrupt-label.pdf"
    label.write_bytes(b"not a PDF")
    result = listing_prep.prepare_listing(listing_payload(label), tmp_path / "out", as_of="2026-10-10")
    assert result["result"] == "uncertain — please check"
    assert result["spl_zip"] is None
    assert "ingredient label/source document" in result["please_confirm"]


def test_missing_required_fields_stays_uncertain_and_never_invents_values(tmp_path, monkeypatch):
    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    incomplete = listing_payload(label)
    incomplete.pop("facility_fei")
    incomplete["facility_exempt"] = None
    incomplete.pop("ingredients")
    result = listing_prep.prepare_listing(incomplete, tmp_path, as_of="2026-10-10")

    assert result["result"] == "uncertain — please check"
    assert result["spl_zip"] is None
    assert any(item["verdict"] == "uncertain" for item in result["rules"]["results"])
    assert not result["fields"]["facility_fei"]["value"]


def test_shopify_connector_products_merge_with_brand_confirmed_details(tmp_path, monkeypatch):
    from ventures.blocks.connectors import ShopifyClient

    monkeypatch.setattr(ShopifyClient, "__init__", lambda self, _shop: None)
    monkeypatch.setattr(ShopifyClient, "get_products", lambda self: [{"id": "gid://shopify/Product/1", "title": "Shopify Catalog Title", "handle": "daily-conditioner"}])
    monkeypatch.setattr(ShopifyClient, "close", lambda self: None)
    details = tmp_path / "brand-details.json"
    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture; reader is mocked below")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    details.write_text(json.dumps({
        "brand": {key: value for key, value in listing_payload(label).items() if key not in {"product_name", "shopify_title", "shopify_id", "source", "as_of"}},
        "products": {"gid://shopify/Product/1": {key: value for key, value in listing_payload(label).items() if key not in {"responsible_person_name", "responsible_person_phone", "facility_fei", "facility_exempt", "facilities", "shopify_id", "source", "as_of"}}},
    }), encoding="utf-8")

    result = listing_prep._prepare_from_shopify("example.myshopify.com", details, tmp_path / "out", "2026-10-10")

    assert result["products_read"] == 1
    assert result["ready"] is True
    assert result["products"][0]["result"] == "match"
    assert result["submitted"] is False


def test_shopify_graphql_fixture_produces_source_linked_uncertain_cosmetics_packet(tmp_path, monkeypatch):
    """Acceptance: Shopify catalog data never substitutes for brand-confirmed FDA fields."""
    from ventures.blocks.connectors import ShopifyClient

    graphql_fixture = json.loads((Path(__file__).parents[1] / "fixtures" / "shopify-products.graphql.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(ShopifyClient, "__init__", lambda self, _shop: None)
    monkeypatch.setattr(ShopifyClient, "graphql", lambda self, _query, _variables=None: graphql_fixture["data"])
    monkeypatch.setattr(ShopifyClient, "close", lambda self: None)

    client = ShopifyClient("fixture-store.myshopify.com")
    products = client.get_products()
    assert products[0]["id"] == "gid://shopify/Product/123456789"
    assert products[0]["title"] == "Daily Glow Lotion"

    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture; reader is mocked below")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {
        "fields": {"ingredients": {"value": "Water, Glycerin", "page": 1, "confidence": 0.99, "uncertain": False}},
        "text": "Ingredients: Water, Glycerin",
    })
    details = tmp_path / "brand-details.json"
    details.write_text(json.dumps({
        "brand": {"responsible_person_name": "Example Beauty LLC", "responsible_person_phone": "+1-555-0101", "customer_confirmed": True},
        "products": {products[0]["id"]: {
            "product_name": "Daily Glow Lotion", "product_category_codes": ["06A2"],
            "ingredients": ["Water", "Glycerin"], "ingredient_document": str(label),
            "first_market_date": "2026-10-01", "last_listing_date": "2026-10-01",
        }},
    }), encoding="utf-8")
    result = listing_prep._prepare_from_shopify(
        "fixture-store.myshopify.com", details, tmp_path / "out", "2026-10-10"
    )

    packet = result["products"][0]
    assert packet["result"] == "uncertain — please check"
    assert packet["spl_zip"] is None
    assert packet["submitted"] is False
    assert packet["fields"]["product_name"]["source"].startswith("brand-details.json#")
    assert packet["fields"]["product_name"]["uncertain"] is False
    assert packet["fields"]["ingredients"]["source"].startswith("label:")
    assert packet["fields"]["facility_fei"]["uncertain"] is True
    assert packet["fields"]["facility_fei"]["value"] == []
    assert all(field.get("source") and isinstance(field.get("uncertain"), bool) for field in packet["fields"].values())
    assert {item["field"] for item in packet["ingredient_checklist"]} >= {"ingredient_order", "label_source", "brand_confirmation"}
    assert packet["reminders"] == {"first_marketed": "2026-10-01", "initial_listing_due": "2027-01-29", "annual_update_review": "2027-10-01"}

    details_without_label_name = json.loads(details.read_text(encoding="utf-8"))
    details_without_label_name["products"][products[0]["id"]].pop("product_name")
    details.write_text(json.dumps(details_without_label_name), encoding="utf-8")
    uncertain = listing_prep._prepare_from_shopify(
        "fixture-store.myshopify.com", details, tmp_path / "out-no-label-name", "2026-10-10"
    )["products"][0]
    assert uncertain["fields"]["product_name"]["value"] is None
    assert uncertain["fields"]["product_name"]["uncertain"] is True
    assert uncertain["fields"]["shopify_title"]["uncertain"] is True


def test_shopify_owner_check_is_read_only(monkeypatch, capsys):
    """Owner connection check may inspect the store but cannot mutate it."""
    from ventures.blocks.connectors import ShopifyClient
    owner_check_path = Path(__file__).parents[1] / "scripts" / "shopify_owner_check.py"
    owner_check_spec = importlib.util.spec_from_file_location("fda_shopify_owner_check", owner_check_path)
    shopify_owner_check = importlib.util.module_from_spec(owner_check_spec)
    assert owner_check_spec and owner_check_spec.loader
    owner_check_spec.loader.exec_module(shopify_owner_check)

    calls = []
    monkeypatch.setattr(ShopifyClient, "__init__", lambda self, _shop: None)
    monkeypatch.setattr(ShopifyClient, "test_connection", lambda self: calls.append("connection") or {"connected": True, "shop": "fixture-store.myshopify.com"})
    monkeypatch.setattr(ShopifyClient, "get_products", lambda self: calls.append("read_products") or [{"id": "gid://shopify/Product/1", "title": "Test"}])
    monkeypatch.setattr(ShopifyClient, "close", lambda self: None)

    assert shopify_owner_check.main(["fixture-store.myshopify.com"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["connected"] is True
    assert report["products_read"] == 1
    assert report["read_only"] is True
    assert calls == ["connection", "read_products"]


def test_missing_shopify_connection_is_a_setup_step_not_a_failed_command(tmp_path, monkeypatch, capsys):
    from ventures.blocks.connectors import ConnectorError, ShopifyClient

    def no_connection(self, _shop):
        raise ConnectorError("Shopify setup is not configured")

    monkeypatch.setattr(ShopifyClient, "__init__", no_connection)
    details = tmp_path / "brand-details.json"
    details.write_text(json.dumps({"brand": {}, "products": {}}), encoding="utf-8")

    result = listing_prep.main([
        "prepare", "--shop", "example.myshopify.com", "--details", str(details),
        "--output", str(tmp_path / "out"),
    ])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["setup_required"]
    assert output["submitted"] is False


def test_uncertain_shopify_product_review_is_a_successful_owner_handoff(tmp_path, monkeypatch, capsys):
    from ventures.blocks.connectors import ShopifyClient

    monkeypatch.setattr(ShopifyClient, "__init__", lambda self, _shop: None)
    monkeypatch.setattr(ShopifyClient, "get_products", lambda self: [{"id": "gid://shopify/Product/1", "title": "Catalog title"}])
    monkeypatch.setattr(ShopifyClient, "close", lambda self: None)
    details = tmp_path / "brand-details.json"
    details.write_text(json.dumps({"brand": {}, "products": {}}), encoding="utf-8")

    result = listing_prep.main([
        "prepare", "--shop", "fixture-store.myshopify.com", "--details", str(details),
        "--output", str(tmp_path / "out"),
    ])

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["products_read"] == 1
    assert output["products"][0]["result"] == "uncertain — please check"
    assert output["submitted"] is False


def test_120_day_and_annual_reminders_are_registered(tmp_path, monkeypatch):
    label = tmp_path / "label.pdf"
    label.write_bytes(b"synthetic fixture; reader is mocked below")
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    recorded = []
    monkeypatch.setattr(listing_prep, "add_deadline", lambda *args: recorded.append(args))
    result = listing_prep.prepare_listing(
        listing_payload(label, first_market_date="2026-10-01", last_listing_date="2026-10-01", shopify_id="gid://Product/1"),
        tmp_path,
        as_of="2026-10-10",
    )

    assert result["result"] == "match"
    assert {row[2] for row in recorded} == {"120d", "365d"}
    assert len(recorded) == 2


def test_due_command_succeeds_when_no_reminders_are_due(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier-home"))
    output = tmp_path / "out" / "due-reminders.json"

    assert listing_prep.main(["due", "--on", "2026-10-10", "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert json.loads(output.read_text(encoding="utf-8")) == []


def test_fda_response_parser_records_customer_status_without_submitting(tmp_path):
    response = tmp_path / "response.txt"
    response.write_text("FDA Cosmetics Direct: Submission Accepted\nConfirmation Number: CSM-12345", encoding="utf-8")

    result = listing_prep.parse_response(response)

    assert result == {"status": "match", "confirmation": "CSM-12345", "submitted_by_glacier": False}


def test_manifest_and_flow_keep_fda_submission_as_customer_step():
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
    flow = json.loads((root / "flows" / "prepare-listing-packet.json").read_text(encoding="utf-8"))

    assert manifest["slug"] == "fda-cosmetics"
    assert len(manifest["your_steps"]) <= 3
    assert any(row["purpose"].lower().find("deadline") >= 0 for row in manifest["schedules"])
    approvals = [node for node in flow["nodes"] if node["type"] == "approval"]
    assert len(approvals) == 1
    assert approvals[0]["config"]["prompt"].startswith("Your step:")
    assert "FDA" in approvals[0]["config"]["prompt"]
    assert all(node["type"] != "command" or "submit" not in node["config"]["cmd"].lower() for node in flow["nodes"])


def test_owner_steps_are_limited_to_connection_and_review_submission():
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
    assert [step["id"] for step in manifest["your_steps"]] == ["connect-shopify", "submit-listing"]
    assert "reminder" in manifest["your_steps"][1]["detail"].lower()
