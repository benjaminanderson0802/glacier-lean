"""Independent carrier packet and ShipStation export acceptance checks."""
import csv
import sys
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "freight-claims"))

def load_csv_intake():
    spec = importlib.util.spec_from_file_location("acceptance_freight_csv_intake", ROOT / "freight-claims/scripts/csv_intake.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shipstation_fixture_maps_delivery_to_claim_candidate():
    parse_shipments_csv = load_csv_intake().parse_shipments_csv
    fixture = Path(__file__).parent / "fixtures/shipstation-shipments.csv"
    rows, skipped = parse_shipments_csv(fixture)
    assert not skipped and len(rows) == 1
    assert rows[0]["tracking_number"] == "1Z999AA10123456784"
    assert rows[0]["carrier"].lower() == "ups"
    assert rows[0]["shipment_id"] == "SHIP-9001"


def test_shipstation_fixture_is_csv_with_order_tracking_and_carrier():
    with (Path(__file__).parent / "fixtures/shipstation-shipments.csv").open(newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["Order Number"] and row["Tracking Number"] and row["Carrier"]


def test_claim_submission_and_invoice_remain_owner_approved():
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text(encoding="utf-8").lower()
    assert "shipper" in readme and ("approve" in readme or "review" in readme)
    assert "send" in readme and "owner" in readme


@pytest.mark.xfail(strict=False, reason="awaiting builder V-FREIGHT2")
def test_carrier_specific_packet_templates_cover_deadlines_and_evidence():
    import pytest
    root = Path(__file__).resolve().parents[2]
    templates = root / "carrier-templates"
    assert templates.is_dir()
    contents = "\n".join(p.read_text(errors="ignore").lower() for p in templates.rglob("*") if p.is_file())
    for carrier in ("ups", "fedex", "usps", "ltl", "carmack"):
        assert carrier in contents
    assert "deadline" in contents and "evidence" in contents and "response" in contents
