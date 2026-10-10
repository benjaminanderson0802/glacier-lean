from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest

from ventures.blocks import deadlines
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from claims import (
    build_contingency_invoice,
    build_claim_packet,
    classify_shipments,
    prepare_mock_carrier_form,
    record_carrier_receipt,
    schedule_claim_deadlines,
    watch_shipments,
)


@pytest.fixture
def complete_claim(tmp_path, monkeypatch):
    docs = {}
    for kind in ("delivery_receipt", "photos", "commercial_invoice", "bill_of_lading"):
        path = tmp_path / f"{kind}.txt"
        path.write_text(f"{kind}: supporting document\n", encoding="utf-8")
        docs[kind] = [str(path)]
    monkeypatch.setattr("claims.read_document", lambda path, schema=None: {
        "fields": {}, "text": Path(path).read_text(encoding="utf-8")
    })
    return {
        "shipment": {
            "shipment_id": "ss-1001",
            "carrier": "Test Freight",
            "tracking_number": "TRK-1001",
            "delivered_date": "2026-09-01",
            "weight_lb": 100,
        },
        "damaged_items": [
            {"description": "widget A", "quantity": 2, "invoice_unit_price": "125.00", "damaged": True, "customer_confirmed": True},
            {"description": "widget B", "quantity": 1, "invoice_unit_price": "80.00", "damaged": False},
        ],
        "documents": docs,
        "carrier_terms": {
            "liability_per_lb": "2.00",
            "source_url": "https://carrier.example.test/terms",
            "effective_date": "2026-01-01",
            "customer_confirmed": True,
        },
        "separate_insurance": False,
        "customer_requests_claim": False,
        "carrier_claim_email": "claims@carrier.example.test",
    }


def test_packet_claims_only_damaged_invoice_items_and_cites_carrier_terms(complete_claim, tmp_path):
    packet = build_claim_packet(complete_claim, evidence_dir=tmp_path / "packets")

    assert packet["result"] == "match"
    assert packet["claimed_value"] == "250.00"
    assert packet["liability_limit_estimate"] == "200.00"
    assert packet["carrier_terms"]["source_url"].startswith("https://")
    assert packet["customer_email_draft"]["sent"] is False
    assert "widget A" in packet["customer_email_draft"]["body"]
    assert "widget B" not in packet["customer_email_draft"]["body"]


def test_missing_required_document_is_uncertain_and_packet_cannot_be_sent(complete_claim):
    complete_claim["documents"].pop("photos")

    packet = build_claim_packet(complete_claim)

    assert packet["result"] == "uncertain — please check"
    assert "photos" in packet["missing_documents"]
    assert packet["customer_email_draft"] is None


def test_damaged_item_values_require_customer_invoice_confirmation(complete_claim):
    complete_claim["damaged_items"][0].pop("customer_confirmed")

    packet = build_claim_packet(complete_claim)

    assert packet["result"] == "uncertain — please check"
    assert packet["damaged_item_values_confirmed_by_customer"] is False
    assert packet["customer_email_draft"] is None


def test_separately_insured_shipment_needs_explicit_customer_request(complete_claim):
    complete_claim["separate_insurance"] = True

    packet = build_claim_packet(complete_claim)
    assert packet["result"] == "uncertain — please check"
    assert packet["customer_email_draft"] is None

    complete_claim["customer_requests_claim"] = True
    packet = build_claim_packet(complete_claim)
    assert packet["result"] == "match"
    assert packet["insurance_instruction"] == "customer explicitly requested carrier claim despite separate insurance"


def test_invalid_or_missing_carrier_terms_remain_uncertain(complete_claim):
    complete_claim["carrier_terms"].pop("source_url")

    packet = build_claim_packet(complete_claim)

    assert packet["result"] == "uncertain — please check"
    assert packet["liability_limit_estimate"] is None


def test_claim_draft_requires_a_valid_carrier_recipient(complete_claim):
    complete_claim["carrier_claim_email"] = ""

    packet = build_claim_packet(complete_claim)

    assert packet["result"] == "uncertain — please check"
    assert packet["customer_email_draft"] is None


def test_carrier_terms_require_shipper_confirmation(complete_claim):
    complete_claim["carrier_terms"].pop("customer_confirmed")

    packet = build_claim_packet(complete_claim)

    assert packet["result"] == "uncertain — please check"
    assert packet["customer_email_draft"] is None


def test_contingency_invoice_is_only_a_draft_after_recovery():
    invoice = build_contingency_invoice("claim-1", "1000.00", 25)
    assert invoice["invoice_amount"] == "250.00"
    assert invoice["status"] == "pending approval"
    assert invoice["sent"] is False and invoice["charged"] is False
    with pytest.raises(ValueError):
        build_contingency_invoice("claim-1", "1000.00", 31)


def test_shared_filer_is_restricted_to_loopback_mock(monkeypatch):
    monkeypatch.setattr("claims.prepare_portal_draft", lambda portal, fields, auth: {"status": "prepared", "portal_id": portal})
    assert prepare_mock_carrier_form("mock", {"claim": "1"}, {
        "base_url": "http://127.0.0.1:7777", "username": "test", "password": "test"
    })["status"] == "prepared"
    with pytest.raises(ValueError, match="local mock"):
        prepare_mock_carrier_form("real", {"claim": "1"}, {
            "base_url": "https://carrier.example/claims", "username": "test", "password": "test"
        })


def test_signature_request_uses_owner_supplied_document_and_shared_customer_block(tmp_path, monkeypatch):
    import ventures.blocks.customer as customer
    document = tmp_path / "owner-approved-authorization.pdf"
    document.write_bytes(b"owner-provided authorization")
    received = {}

    def request_signature(path, signer):
        received.update(path=path, signer=signer)
        return {"status": "pending_signature", "url": "http://127.0.0.1:8765/sign/test"}

    monkeypatch.setattr(customer, "request_signature", request_signature)
    result = __import__("claims").request_shipper_authorization(str(document), {"name": "Test Shipper"})

    assert result["status"] == "pending_signature"
    assert received == {"path": str(document), "signer": {"name": "Test Shipper"}}


def test_deadline_block_tracks_30_and_120_days_once(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    schedule_claim_deadlines("claim-1", "2026-09-01")

    day30 = deadlines.due(date(2026, 10, 1))
    assert len(day30) == 1 and day30[0]["rule"] == "30d|120d"
    assert deadlines.due(date(2026, 10, 1)) == []
    day120 = deadlines.due(date(2026, 12, 30))
    assert len(day120) == 1
    assert any(step["type"] == "approval" for step in day30[0]["glacier_steps"])


def test_customer_receipt_confirmation_starts_deadlines(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    confirmation = tmp_path / "carrier-confirmation.pdf"
    confirmation.write_bytes(b"customer-provided test confirmation")

    record = record_carrier_receipt("claim-9", "2026-09-01", "REF-9", str(confirmation), output_dir=tmp_path / "reports")

    assert record["result"] == "match"
    assert record["deadline_rule"] == "30d|120d"
    assert Path(record["record_path"]).is_file()
    assert record["side_effects"] == []
    assert deadlines.due(date(2026, 10, 1))[0]["item_id"] == "claim-9"


def test_shipstation_exceptions_are_candidates_not_claims():
    rows = [
        {"shipment_id": "1", "shipment_status": "shipped", "tracking_status": "exception", "exception_description": "pallet damage"},
        {"shipment_id": "2", "shipment_status": "shipped", "tracking_status": "in_transit"},
    ]

    candidates = classify_shipments(rows)

    assert candidates == [{"shipment_id": "1", "signal": "possible damage or delivery exception", "customer_confirmation_required": True}]


def test_shipstation_reads_are_opt_in_and_tracking_exceptions_are_customer_confirmed(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))

    class FakeShipStation:
        def __init__(self):
            self.tracked = []

        def get_shipments(self, **kwargs):
            return [{"shipment_id": "ss-7", "labels": [{"label_id": "label-7"}]}]

        def get_tracking_for_label(self, label_id):
            self.tracked.append(label_id)
            return {"status_code": "EX", "status_description": "Exception", "exception_description": "Pallet damaged"}

    client = FakeShipStation()
    disabled = watch_shipments(client=client, enabled=False)
    assert disabled["result"] == "uncertain — please check"
    assert client.tracked == []

    record = watch_shipments(client=client, enabled=True)
    assert client.tracked == ["label-7"]
    assert record["result"] == "match"
    assert record["candidates"][0]["customer_confirmation_required"] is True
