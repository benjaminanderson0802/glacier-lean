from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from carrier_claims import carrier_guidance, filing_deadline, response_schedule
from claims import prepare_csv_packets


FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("carrier", "days", "anchor"),
    [
        ("UPS", 60, "scheduled_delivery_date"),
        ("FedEx", 60, "shipment_date"),
        ("USPS", 60, "mailing_date"),
    ],
)
def test_parcel_deadlines_have_carrier_specific_anchor(carrier, days, anchor):
    guidance = carrier_guidance(carrier, shipment_type="damage")

    assert guidance["filing_deadline_days"] == days
    assert guidance["filing_deadline_anchor"] == anchor
    assert guidance["sources"]
    assert filing_deadline(carrier, date(2026, 1, 1), shipment_type="damage") == date(2026, 3, 2)


def test_fedex_international_damage_deadline_is_21_days():
    assert filing_deadline(
        "FedEx", date(2026, 1, 1), shipment_type="damage", international=True
    ) == date(2026, 1, 22)


def test_usps_lost_claim_requires_service_window_instead_of_guessing():
    guidance = carrier_guidance("USPS", shipment_type="lost")

    assert guidance["filing_deadline_days"] is None
    assert guidance["deadline_requires_service_lookup"] is True


def test_ltl_packet_includes_carmack_evidence_and_response_milestones():
    guidance = carrier_guidance("LTL", shipment_type="damage")
    schedule = response_schedule("LTL", date(2026, 1, 1))

    assert guidance["filing_deadline_months"] == 9
    assert "written claim with shipment identity, asserted liability, and a determinable amount" in guidance["required_evidence"]
    assert [item["due_on"] for item in schedule] == ["2026-01-31", "2026-05-01"]
    assert guidance["sources"]


def test_shipstation_csv_fixture_to_carrier_claim_packets(tmp_path):
    csv_path = tmp_path / "shipstation.csv"
    csv_path.write_text(
        "Order Number,Ship Date,Carrier,Service,Tracking Number,Weight,Status\n"
        "42,2026-01-01,UPS,Ground,1ZFIXTURE42,10,Exception - damaged\n",
        encoding="utf-8",
    )
    intake = [{
        "shipment_id": "SS-ORD-42",
        "shipment_type": "damage",
        "scheduled_delivery_date": "2026-01-05",
        "damaged_items": [{
            "description": "Fixture tile", "quantity": 1,
            "invoice_unit_price": "125.00", "damaged": True,
            "customer_confirmed": True,
        }],
        "documents": {
            "delivery_receipt": [str(FIXTURES / "delivery-receipt.txt")],
            "photos": [str(FIXTURES / "damage-photo-note.txt")],
            "commercial_invoice": [str(FIXTURES / "commercial-invoice.txt")],
            "bill_of_lading": [str(ROOT / "ventures/blocks/reader/samples/documents/sample-bill-of-lading.pdf")],
        },
        "carrier_terms": {
            "source_url": "https://www.ups.com/us/en/support/file-a-claim",
            "effective_date": "2026-01-01", "customer_confirmed": True,
            "liability_per_lb": "2.00",
        },
        "carrier_claim_email": "claims@example.test",
    }]

    result = prepare_csv_packets(csv_path, intake, tmp_path / "packets")

    assert result["source"] == "csv"
    assert result["packet_count"] == 1
    packet = result["packets"][0]
    assert packet["shipment_id"] == "SS-ORD-42"
    assert packet["carrier"] == "UPS"
    assert packet["claimed_value"] == "125.00"
    assert packet["carrier_claim_guidance"]["filing_deadline"] == "2026-03-06"
    assert packet["customer_email_draft"]["sent"] is False
    assert packet["side_effects"] == []
    assert Path(packet["packet_path"]).is_file()


def test_customer_intake_checklist_exists_and_preserves_owner_filing_step():
    checklist = (FIXTURES.parent.parent / "incoming" / "CUSTOMER-INTAKE.md").read_text(encoding="utf-8")

    assert "bill of lading" in checklist.lower()
    assert "carrier receipt" in checklist.lower()
    assert "shipper submits" in checklist.lower()
