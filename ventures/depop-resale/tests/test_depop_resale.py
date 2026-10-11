import csv
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import depop_prep  # noqa: E402


def test_manifest_is_valid_and_has_one_human_step():
    schema = json.loads((ROOT.parent / "venture.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "venture.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    assert len(manifest["your_steps"]) == 1
    assert "photo" in manifest["your_steps"][0]["detail"].lower()
    assert "ship" in manifest["your_steps"][0]["detail"].lower()


def test_buy_ceilings_ranked_categories_use_net_margin_target():
    categories = depop_prep.category_research()
    assert len(categories) == 5
    assert [row["rank"] for row in categories] == [1, 2, 3, 4, 5]
    ceiling = depop_prep.max_buy_price(
        expected_sale=40, target_margin=0.50, processing_rate=0.033,
        processing_flat=0.45, seller_shipping=0, packaging=1.0
    )
    assert ceiling == pytest.approx(17.23)


def test_fixture_listing_csv_uses_only_supplied_facts_and_owner_photos(tmp_path):
    source = ROOT / "tests" / "fixtures" / "inventory.csv"
    rows = depop_prep.read_inventory(source)
    prepared = depop_prep.prepare_listings(rows, photo_root=ROOT / "tests" / "fixtures")
    assert len(prepared) == 1
    listing = prepared[0]
    assert listing["title"] == "Vintage Denim Jacket Blue Large"
    assert listing["size"] == "Large"
    assert listing["condition"] == "Good"
    assert listing["price_usd"] == "42.00"
    assert listing["tags"].split("|")[0] == "vintage"
    assert "light cuff wear" in listing["description"].lower()
    output = tmp_path / "handoff.csv"
    depop_prep.write_handoff_csv(prepared, output)
    with output.open(newline="", encoding="utf-8") as handle:
        exported = next(csv.DictReader(handle))
    assert exported["photo_paths"] == "photos/jacket-front.jpg|photos/jacket-back.jpg"
    assert "depop.com" not in output.read_text(encoding="utf-8").lower()


def test_listing_refuses_supplier_or_stock_photos_and_incomplete_item_facts():
    row = depop_prep.read_inventory(ROOT / "tests" / "fixtures" / "inventory.csv")[0]
    row["photo_origin"] = "supplier"
    with pytest.raises(ValueError, match="owner_original"):
        depop_prep.prepare_listings([row], photo_root=ROOT / "tests" / "fixtures")
    row["photo_origin"] = "owner_original"
    row["condition"] = ""
    with pytest.raises(ValueError, match="condition"):
        depop_prep.prepare_listings([row], photo_root=ROOT / "tests" / "fixtures")


def test_shipping_checklist_requires_sold_item_and_never_buys_label(tmp_path):
    checklist = depop_prep.shipping_checklist(
        item_id="JKT-001", buyer_name="Test Buyer", sold_at="2026-10-11",
        carrier="USPS", label_reference="owner-to-add-after-purchase"
    )
    out = tmp_path / "shipping.md"
    depop_prep.write_shipping_checklist(checklist, out)
    text = out.read_text(encoding="utf-8")
    assert "Confirm sold order in Depop" in text
    assert "buy or generate" in text.lower()
    assert "Mark as shipped" in text
    assert "owner-to-add-after-purchase" in text
    assert "packing slip" in text.lower()


def test_research_and_owner_steps_cite_current_policy_and_limit_scope():
    research = (ROOT / "RESEARCH.md").read_text(encoding="utf-8")
    owner_steps = (ROOT / "OWNER-STEPS.md").read_text(encoding="utf-8").lower()
    assert "22499808769553-dropshipping-policy" in research
    assert "360001773148-terms-of-service" in research
    assert "4411154329233" in research
    assert "original photos" in research.lower()
    assert "no depop account access" in research.lower()
    assert "click" in owner_steps
    assert "publish" in owner_steps

