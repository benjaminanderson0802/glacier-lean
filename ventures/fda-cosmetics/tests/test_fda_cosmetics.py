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


def listing_payload(**updates):
    payload = {
        "responsible_person_name": "Example Beauty LLC",
        "responsible_person_phone": "+1-555-0101",
        "product_category_codes": ["06A2"],
        "product_name": "Daily Conditioner",
        "fragrance_or_flavor": ["fragrance"],
        "facility_fei": ["1234567890"],
        "facility_exempt": False,
        "facilities": [{"fei": "1234567890", "exempt_confirmed": False}],
        "ingredients": ["Water", "Glycerin", "Fragrance"],
        "ingredient_document": "label.pdf",
        "exemption_checklist": {"small_business": False, "product_may_be_covered_exception": False, "customer_wants_listing": True},
        "customer_confirmed": True,
        "source": "owner-upload",
        "as_of": "2026-10-10",
    }
    payload.update(updates)
    return payload


def test_valid_customer_confirmed_listing_builds_customer_submit_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    result = listing_prep.prepare_listing(listing_payload(), tmp_path, as_of="2026-10-10")

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
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {
        "fields": {"ingredients": {"value": "Water, Glycerin", "page": 1, "confidence": 0.51, "uncertain": True}},
        "text": "Ingredients: Water, Glycerin",
    })
    result = listing_prep.prepare_listing(
        listing_payload(customer_confirmed=False, ingredient_document="label.pdf"),
        tmp_path,
        as_of="2026-10-10",
    )

    assert result["result"] == "uncertain — please check"
    assert result["spl_zip"] is None
    assert "ingredients" in result["please_confirm"]
    assert not list(tmp_path.glob("*.zip"))


def test_missing_required_fields_stays_uncertain_and_never_invents_values(tmp_path):
    incomplete = listing_payload()
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
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    details.write_text(json.dumps({
        "brand": {key: value for key, value in listing_payload().items() if key not in {"product_name", "shopify_title", "shopify_id", "source", "as_of"}},
        "products": {"gid://shopify/Product/1": {key: value for key, value in listing_payload().items() if key not in {"responsible_person_name", "responsible_person_phone", "facility_fei", "facility_exempt", "facilities", "shopify_id", "source", "as_of"}}},
    }), encoding="utf-8")

    result = listing_prep._prepare_from_shopify("example.myshopify.com", details, tmp_path / "out", "2026-10-10")

    assert result["products_read"] == 1
    assert result["ready"] is True
    assert result["products"][0]["result"] == "match"
    assert result["submitted"] is False


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


def test_120_day_and_annual_reminders_are_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(listing_prep, "read_document", lambda *_args, **_kwargs: {"fields": {"ingredients": {"value": "Water, Glycerin, Fragrance", "page": 1, "confidence": 0.99, "uncertain": False}}, "text": "Ingredients: Water, Glycerin, Fragrance"})
    recorded = []
    monkeypatch.setattr(listing_prep, "add_deadline", lambda *args: recorded.append(args))
    result = listing_prep.prepare_listing(
        listing_payload(first_market_date="2026-10-01", last_listing_date="2026-10-01", shopify_id="gid://Product/1"),
        tmp_path,
        as_of="2026-10-10",
    )

    assert result["result"] == "match"
    assert {row[2] for row in recorded} == {"120d", "365d"}
    assert len(recorded) == 2


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
