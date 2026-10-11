"""Independent Shopify-to-FDA listing packet acceptance checks."""
import json
import sys
import importlib.util
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "fda-cosmetics"))

def load_listing_prep():
    spec = importlib.util.spec_from_file_location("acceptance_fda_listing_prep", ROOT / "fda-cosmetics/scripts/listing_prep.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.xfail(strict=False, reason="awaiting builder V-FDA2")
def test_shopify_graphql_fixture_produces_field_sources_and_uncertainty(tmp_path, monkeypatch):
    listing_prep = load_listing_prep()
    fixture = json.loads((Path(__file__).parent / "fixtures/shopify-products-2026-04-16.json").read_text())
    monkeypatch.setattr(listing_prep, "read_shopify_products", lambda *_a, **_k: fixture)
    result = listing_prep.prepare_from_shopify("glacier-test-cosmetics.myshopify.com", tmp_path / "details.json", tmp_path / "out")
    assert result.get("result") in {"match", "ready"}
    fields = result.get("fields", result.get("listing", {}))
    assert fields
    assert any("source" in str(v).lower() for v in fields.values())
    assert "uncertain" in str(result).lower() or "confirm" in str(result).lower()


def test_fda_packet_never_submits_and_keeps_customer_review_gate():
    prepare_listing = load_listing_prep().prepare_listing
    assert callable(prepare_listing)
    source = Path(__file__).resolve().parents[2] / "flows/prepare-listing-packet.json"
    flow = json.loads(source.read_text())
    serialized = json.dumps(flow).lower()
    assert "has not signed or submitted anything" in serialized
    assert "customer_submit" in serialized or "approval" in serialized


def test_reminder_flow_contains_120_day_and_annual_cadence():
    flow = json.loads((Path(__file__).resolve().parents[2] / "flows/daily-deadline-reminders.json").read_text())
    serialized = json.dumps(flow).lower()
    assert "120" in serialized and ("annual" in serialized or "year" in serialized)
