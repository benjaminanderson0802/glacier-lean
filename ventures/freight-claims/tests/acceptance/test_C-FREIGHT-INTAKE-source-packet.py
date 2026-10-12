"""Independent source-to-packet cases for freight claim intake (synthetic only)."""
from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "freight-claims" / "scripts"))
from claims import prepare_csv_packets  # noqa: E402


EVIDENCE = ROOT / "freight-claims" / "tests" / "fixtures"
READER_BOL = ROOT / "blocks" / "reader" / "samples" / "documents" / "sample-bill-of-lading.pdf"
RULE_SOURCE_HOSTS = {
    "ups": {"www.ups.com"},
    "fedex": {"www.fedex.com"},
    "ltl": {"www.govinfo.gov", "www.ecfr.gov"},
}


def _csv(tmp_path: Path, *, carrier: str, service: str, shipment_id: str,
         tracking: str, ship_date: str, status: str = "Exception - damaged pallet") -> Path:
    path = tmp_path / f"{shipment_id}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "Shipment ID", "Order Number", "Ship Date", "Carrier", "Service",
            "Tracking Number", "Weight", "Ship To Country", "Status",
        ])
        writer.writeheader()
        writer.writerow({
            "Shipment ID": shipment_id, "Order Number": f"ORDER-{shipment_id}",
            "Ship Date": ship_date, "Carrier": carrier, "Service": service,
            "Tracking Number": tracking, "Weight": "100", "Ship To Country": "US",
            "Status": status,
        })
    return path


def _intake(*, shipment_id: str, carrier_email: str = "claims@example.test",
            issue: str = "damage", scheduled_delivery: str | None = "2026-10-10",
            delivered: str | None = "2026-10-11", international: bool = False,
            all_documents: bool = True) -> dict:
    documents = {
        "delivery_receipt": [str(EVIDENCE / "delivery-receipt.txt")],
        "photos": [str(EVIDENCE / "damage-photo-note.txt")],
        "commercial_invoice": [str(EVIDENCE / "commercial-invoice.txt")],
        "bill_of_lading": [str(READER_BOL)],
    }
    if not all_documents:
        documents.pop("photos")
    claim = {
        "shipment_id": shipment_id,
        "shipment_type": issue,
        "international": international,
        "damaged_items": [{
            "description": "Synthetic ceramic tile", "quantity": 2,
            "invoice_unit_price": "125.00", "damaged": True,
            "customer_confirmed": True,
        }],
        "documents": documents,
        "carrier_terms": {
            "source_url": "https://carrier.example.test/synthetic-terms",
            "effective_date": "2026-01-01", "customer_confirmed": True,
            "liability_per_lb": "2.00",
        },
        "carrier_claim_email": carrier_email,
        "separate_insurance": False,
        "customer_requests_claim": False,
    }
    if scheduled_delivery:
        claim["scheduled_delivery_date"] = scheduled_delivery
    if delivered:
        claim["delivered_date"] = delivered
    return claim


@pytest.mark.parametrize(
    ("carrier", "service", "ship_date", "issue", "scheduled_delivery", "delivered", "international", "expected_template", "anchor", "days"),
    [
        ("UPS", "Ground", "2026-10-01", "damage", "2026-10-10", "2026-10-11", False, "ups", "2026-10-10", 60),
        ("FedEx", "Home Delivery", "2026-10-01", "damage", None, "2026-10-11", False, "fedex", "2026-10-01", 60),
        ("FedEx", "International", "2026-10-01", "damage", None, "2026-10-11", True, "fedex", "2026-10-01", 21),
        ("Northstar Freight", "LTL", "2026-10-01", "damage", None, "2026-10-11", False, "ltl", "2026-10-11", 0),
    ],
)
def test_source_row_and_customer_sources_map_to_packet_and_deadline(
    tmp_path, carrier, service, ship_date, issue, scheduled_delivery, delivered,
    international, expected_template, anchor, days,
):
    shipment_id = f"SHIP-{expected_template}-{international}"
    csv_path = _csv(tmp_path, carrier=carrier, service=service, shipment_id=shipment_id,
                    tracking=f"TRACK-{shipment_id}", ship_date=ship_date)
    intake = _intake(shipment_id=shipment_id, issue=issue,
                     scheduled_delivery=scheduled_delivery, delivered=delivered,
                     international=international)

    result = prepare_csv_packets(csv_path, intake, tmp_path / "packets")

    assert result["source"] == "csv"
    assert result["csv_file"] == str(csv_path)
    assert result["candidate_count"] == result["packet_count"] == 1
    packet = result["packets"][0]
    # Shipment identity and carrier facts must agree with the corresponding CSV row.
    assert packet["shipment_id"] == shipment_id
    assert packet["carrier"] == carrier
    assert packet["tracking_number"] == f"TRACK-{shipment_id}"
    # Claim amount, affected items, and attached evidence must agree with customer sources.
    assert packet["claimed_value"] == "250.00"
    assert packet["damaged_items"] == [{
        "description": "Synthetic ceramic tile", "quantity": 2,
        "invoice_unit_price": "125.00", "claimed_value": "250.00",
        "customer_confirmed": True,
    }]
    expected_files = {str(Path(path).resolve()) for paths in intake["documents"].values() for path in paths}
    assert {path for paths in packet["documents"].values() for path in paths} == expected_files
    assert {read["path"] for read in packet["document_reads"]} == expected_files
    # Carrier deadline metadata must retain its date anchor and cite the carrier rule source.
    guidance = packet["carrier_claim_guidance"]
    assert guidance["template_id"] == expected_template
    assert guidance["deadline_anchor_date"] == anchor
    if days:
        expected_deadline = date.fromisoformat(anchor) + timedelta(days=days)
        assert guidance["filing_deadline"] == expected_deadline.isoformat()
    else:
        assert guidance["filing_deadline"] == "2027-07-11"
    assert guidance["sources"]
    assert {urlparse(source["url"]).netloc for source in guidance["sources"]} <= RULE_SOURCE_HOSTS[expected_template]
    assert packet["carrier_terms"]["source_url"] == intake["carrier_terms"]["source_url"]
    assert packet["customer_email_draft"]["sent"] is False
    assert packet["customer_email_draft"]["body"].endswith(
        "This draft has not been sent; the customer must review it and submit it through their chosen carrier channel."
    )
    assert packet.get("recovery_confirmed") is not True
    assert packet.get("filing_authorized") is not True
    assert packet.get("filed") is not True
    assert packet.get("submitted") is not True
    assert packet["side_effects"] == []
    assert packet["human_review_required"] is True
    assert result["side_effects"] == []


def test_missing_and_unsupported_source_rows_stay_uncertain_and_unfiled(tmp_path):
    csv_path = tmp_path / "mixed.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "Shipment ID", "Ship Date", "Carrier", "Service", "Tracking Number", "Weight", "Status",
        ])
        writer.writeheader()
        writer.writerow({"Shipment ID": "SHIP-NO-INTAKE", "Ship Date": "2026-10-01",
                         "Carrier": "UPS", "Service": "Ground", "Tracking Number": "TRACK-MISSING",
                         "Weight": "100", "Status": "Exception - damaged"})
        writer.writerow({"Shipment ID": "SHIP-UNKNOWN-CARRIER", "Ship Date": "2026-10-01",
                         "Carrier": "Mystery Parcel Co", "Service": "Mystery Service",
                         "Tracking Number": "TRACK-UNKNOWN", "Weight": "100",
                         "Status": "Exception - damaged"})
    complete_but_unsupported = _intake(shipment_id="SHIP-UNKNOWN-CARRIER")

    result = prepare_csv_packets(csv_path, [complete_but_unsupported], tmp_path / "packets")

    assert result["result"] == "uncertain — please check"
    assert result["needs_customer_intake"][0]["shipment_id"] == "SHIP-NO-INTAKE"
    assert result["packet_count"] == 1
    packet = result["packets"][0]
    assert packet["result"] == "uncertain — please check"
    assert packet["carrier_claim_guidance"]["template_id"] == "manual-review"
    assert packet["carrier_claim_guidance"]["filing_deadline"] is None
    assert packet["customer_email_draft"] is None
    assert packet["side_effects"] == []
    assert result["side_effects"] == []


def test_incomplete_damage_evidence_keeps_packet_uncertain_without_claim_draft(tmp_path):
    shipment_id = "SHIP-PARTIAL-DAMAGE"
    csv_path = _csv(tmp_path, carrier="UPS", service="Ground", shipment_id=shipment_id,
                    tracking="TRACK-PARTIAL", ship_date="2026-10-01")
    intake = _intake(shipment_id=shipment_id, all_documents=False)

    result = prepare_csv_packets(csv_path, intake, tmp_path / "packets")

    packet = result["packets"][0]
    assert result["result"] == packet["result"] == "uncertain — please check"
    assert "photos" in packet["missing_documents"]
    assert packet["customer_email_draft"] is None
    assert packet["side_effects"] == []
    assert result["side_effects"] == []
