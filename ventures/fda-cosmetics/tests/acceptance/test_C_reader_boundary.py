"""Independent reader-to-FDA boundary checks using temporary label examples."""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest

from ventures.blocks import reader


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "reader_boundary_listing_prep", ROOT / "fda-cosmetics/scripts/listing_prep.py"
)
listing_prep = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(listing_prep)


def _label(tmp_path: Path, text: str, name: str = "label.txt") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _engine_pair(first_value: str, second_value: str, *, page: int | None = 1):
    def engine(value: str):
        return lambda *_args: {
            "ingredients": {"value": value, "page": page, "confidence": 0.95}
        }

    return [("independent-label-reader-a", engine(first_value)),
            ("independent-label-reader-b", engine(second_value))]


def _valid_payload(label: Path) -> dict:
    return {
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
        "ingredient_document": str(label),
        "exemption_checklist": {
            "small_business": False,
            "product_may_be_covered_exception": False,
            "customer_wants_listing": True,
        },
        "customer_confirmed": True,
        "source": "independent-label-example",
        "_field_sources": {
            "responsible_person_name": "brand-details.json#/responsible_person_name",
            "responsible_person_phone": "brand-details.json#/responsible_person_phone",
            "responsible_person_role": "brand-details.json#/responsible_person_role",
            "product_category_codes": "brand-details.json#/product_category_codes",
            "product_name": "brand-details.json#/product_name",
            "fragrance_or_flavor": "brand-details.json#/fragrance_or_flavor",
            "facility_fei": "brand-details.json#/facility_fei",
            "facilities": "brand-details.json#/facilities",
            "ingredients": f"label:{label}",
            "first_market_date": "brand-details.json#/first_market_date",
            "last_listing_date": "brand-details.json#/last_listing_date",
            "exemption_checklist": "brand-details.json#/exemption_checklist",
            "customer_confirmed": "brand-details.json#/customer_confirmed",
        },
    }


def _assert_sources_and_ingredient_page(report: dict, label: Path, *, page: int | None):
    # Each prepared FDA field must name its source. The extracted label field
    # additionally carries the source page for review.
    assert report["fields"]
    assert all(field.get("source") for field in report["fields"].values())
    ingredient = report["fields"]["ingredients"]
    assert ingredient["source"] == f"label:{label}"
    assert ingredient["page"] == page


def test_agreeing_independent_readers_preserve_label_field_and_page(tmp_path, monkeypatch):
    # Example A is independent, temporary package-label text; it is not a
    # checked-in fixture or an expected value derived from the parser.
    label = _label(tmp_path, "Daily Conditioner\nIngredients: Water, Glycerin, Fragrance\n")
    monkeypatch.setattr(
        reader, "_available_engines",
        lambda: _engine_pair("Water, Glycerin, Fragrance", "Water, Glycerin, Fragrance"),
    )

    extracted = reader.read_document(label, schema={"ingredients": ["Ingredients", "Ingredient list"]})
    report = listing_prep.prepare_listing(_valid_payload(label), tmp_path / "agreed", as_of="2026-10-10")

    assert extracted["fields"]["ingredients"] == {
        "value": "Water, Glycerin, Fragrance", "page": 1,
        "confidence": 0.95, "uncertain": False,
    }
    assert report["result"] == "match"
    assert report["spl_zip"]
    _assert_sources_and_ingredient_page(report, label, page=1)
    with zipfile.ZipFile(tmp_path / "agreed" / report["spl_zip"]) as archive:
        assert archive.namelist() == [report["spl_xml"]]


def test_disagreeing_independent_readers_keep_review_boundary_closed(tmp_path, monkeypatch):
    # Example B has an intentionally disputed order from reader B. The value
    # representation is left to the shared reader contract; uncertainty is
    # the boundary asserted here.
    label = _label(tmp_path, "Daily Conditioner\nIngredients: Water, Glycerin, Fragrance\n", "disputed-label.txt")
    monkeypatch.setattr(
        reader, "_available_engines",
        lambda: _engine_pair("Water, Glycerin, Fragrance", "Water, Fragrance, Glycerin"),
    )

    extracted = reader.read_document(label, schema={"ingredients": ["Ingredients", "Ingredient list"]})
    out = tmp_path / "disputed"
    report = listing_prep.prepare_listing(_valid_payload(label), out, as_of="2026-10-10")

    assert extracted["fields"]["ingredients"]["uncertain"] is True
    assert extracted["fields"]["ingredients"]["page"] == 1
    assert report["result"] == "uncertain — please check"
    assert report["spl_zip"] is None
    assert "ingredients" in report["please_confirm"]
    _assert_sources_and_ingredient_page(report, label, page=1)
    assert not list(out.glob("*.zip"))


def test_agreement_without_label_page_evidence_is_uncertain_in_shared_reader(tmp_path, monkeypatch):
    label = _label(tmp_path, "Daily Conditioner\nIngredients: Water, Glycerin, Fragrance\n", "no-page-label.txt")
    monkeypatch.setattr(
        reader, "_available_engines",
        lambda: _engine_pair("Water, Glycerin, Fragrance", "Water, Glycerin, Fragrance", page=None),
    )
    extracted = reader.read_document(label, schema={"ingredients": ["Ingredients", "Ingredient list"]})

    assert extracted["fields"]["ingredients"]["uncertain"] is True


def test_agreement_without_label_page_evidence_blocks_fda_packet(tmp_path, monkeypatch):
    label = _label(tmp_path, "Daily Conditioner\nIngredients: Water, Glycerin, Fragrance\n", "no-page-fda-label.txt")
    monkeypatch.setattr(
        reader, "_available_engines",
        lambda: _engine_pair("Water, Glycerin, Fragrance", "Water, Glycerin, Fragrance", page=None),
    )
    out = tmp_path / "no-page"
    report = listing_prep.prepare_listing(_valid_payload(label), out, as_of="2026-10-10")

    assert report["result"] == "uncertain — please check"
    assert report["spl_zip"] is None
    _assert_sources_and_ingredient_page(report, label, page=None)
    assert not list(out.glob("*.zip"))
