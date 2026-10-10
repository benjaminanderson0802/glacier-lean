from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ventures" / "property-tax" / "scripts"))

import property_tax


def certain(value, page=1):
    return {"value": value, "page": page, "confidence": 0.99, "uncertain": False}


def test_packet_uses_reader_citations_and_requires_recent_arms_length_comps(tmp_path, monkeypatch):
    notice = tmp_path / "notice.txt"
    notice.write_text("PIN: 1234567890\nAssessed value: 100000\n")
    comps = []
    for number, (sold, amount, area) in enumerate(
        [("2026-06-01", "500000", "2000"), ("2026-04-01", "480000", "1900"), ("2026-02-01", "510000", "2050")], 1
    ):
        path = tmp_path / f"comp-{number}.txt"
        path.write_text(f"Sale date: {sold}\nSale price: {amount}\nSquare feet: {area}\n")
        comps.append({"path": str(path), "source_url": f"https://records.example.test/sale/{number}", "arms_length_confirmed": True})

    def read_document(path, schema=None):
        name = Path(path).name
        if name == "notice.txt":
            return {"fields": {"parcel_id": certain("1234567890"), "assessed_value": certain("100000")}, "text": "source notice"}
        comp = int(name.split("-")[1].split(".")[0])
        sale_date, sale_price, square_feet = [
            ("2026-06-01", "500000", "2000"),
            ("2026-04-01", "480000", "1900"),
            ("2026-02-01", "510000", "2050"),
        ][comp - 1]
        return {"fields": {"sale_date": certain(sale_date, comp), "sale_price": certain(sale_price, comp), "square_feet": certain(square_feet, comp)}, "text": "public sales record"}

    monkeypatch.setattr(property_tax.reader, "read_document", read_document)
    packet = property_tax.build_packet(
        {"county": "Cook County", "parcel_id": "1234567890", "notice_path": str(notice),
         "notice_date": "2026-06-15", "deadline": "2026-12-15", "subject_square_feet": 2000,
         "customer_requested_value": 95000, "comparables": comps},
        feed_rows=[{"record_id": "1234567890", "data": {"class": "2-11", "township_name": "Example", "zip_code": "60601"}, "source_url": "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.json"}],
        today=date(2026, 6, 15),
    )

    assert packet["result"] == "match"
    assert packet["status"] == "ready_for_customer_review"
    assert packet["filing_submitted"] is False
    assert packet["county"] == "Cook County"
    assert packet["comparables"][0]["sale_date"]["page"] == 1
    assert "the customer" in packet["legal_review_notice"].lower()
    assert packet["customer_requested_value"] == 95000


def test_uncertain_reader_result_never_becomes_a_match(tmp_path, monkeypatch):
    notice = tmp_path / "notice.txt"
    notice.write_text("notice")
    comp = tmp_path / "comp.txt"
    comp.write_text("sale record")
    fields = {
        "sale_date": {"value": "2026-06-01", "page": 1, "confidence": 0.7, "uncertain": True},
        "sale_price": certain("500000"),
        "square_feet": certain("2000"),
    }
    monkeypatch.setattr(property_tax.reader, "read_document", lambda path, schema=None: {"fields": fields, "text": "record"})
    packet = property_tax.build_packet(
        {"county": "Cook County", "parcel_id": "1234567890", "notice_path": str(notice),
         "notice_date": "2026-06-15", "deadline": "2026-12-15", "subject_square_feet": 2000,
         "customer_requested_value": 95000,
         "comparables": [{"path": str(comp), "source_url": "https://records.example.test/sale/1", "arms_length_confirmed": True}]},
        feed_rows=[{"record_id": "1234567890", "data": {"class": "2-11"}, "source_url": "https://data.example.test/roll"}],
        today=date(2026, 6, 15),
    )
    assert packet["result"] == "uncertain — please check"
    assert packet["status"] == "needs_customer_confirmation"
    assert packet["filing_submitted"] is False


def test_missing_roll_parcel_reports_no_match_and_does_not_prepare_packet(tmp_path):
    result = property_tax.find_roll_parcel("999", [])
    assert result["result"] == "no match found in Cook County Assessor parcel roll as of 2026-10-10"
    assert result["parcel"] is None


def test_postcard_preview_uses_shared_mail_block_and_never_sends(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(property_tax.mail, "postcard", lambda *args, **kwargs: calls.append((args, kwargs)) or {"status": "render_only"})
    result = property_tax.prepare_postcard(
        {"sender": "Property Tax Packet Service", "name": "Owner", "address": {"address_line1": "1 Main St", "address_city": "Chicago", "address_state": "IL", "address_zip": "60601"}, "parcel_id": "1234567890", "source_url": "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.json"},
        output_dir=tmp_path,
    )
    assert calls and calls[0][1]["approval_id"] is None
    assert result["status"] == "render_only"
    assert result["external_mail_sent"] is False
    assert "Property Tax Packet Service" in calls[0][0][0]


def test_upload_retention_requires_approval_and_stays_within_venture_folder(tmp_path, monkeypatch):
    home = tmp_path / "home"
    incoming = home / "ventures" / "property-tax" / "incoming"
    incoming.mkdir(parents=True)
    upload = incoming / "notice.pdf"
    upload.write_bytes(b"customer supplied notice")
    closed = incoming / "closed-cases.json"
    closed.write_text(json.dumps([{"case_id": "case-1", "closed_on": "2026-01-01", "uploads": [str(upload)], "keep": False}]))
    monkeypatch.setenv("GLACIER_HOME", str(home))

    plan = property_tax.retention_plan(closed, today=date(2026, 2, 1))
    assert plan["deletes_files"] is False
    assert plan["eligible"] == [{"case_id": "case-1", "path": str(upload.resolve()), "exists": True, "closed_on": "2026-01-01"}]
    plan_path = incoming / "retention-plan.json"
    plan_path.write_text(json.dumps(plan))
    try:
        property_tax.execute_retention(plan_path, "")
    except ValueError as exc:
        assert "approval_id" in str(exc)
    else:
        raise AssertionError("cleanup must require an approval ID")
    assert upload.exists()
    result = property_tax.execute_retention(plan_path, "reviewed-run-1")
    assert result["deleted"] == [str(upload.resolve())]
    assert not upload.exists()


def test_manifest_and_flows_gate_outbound_actions_and_keep_owner_steps_bounded():
    base = ROOT / "ventures" / "property-tax"
    manifest = json.loads((base / "venture.json").read_text())
    assert manifest["slug"] == "property-tax"
    assert len(manifest["your_steps"]) <= 3
    assert manifest["your_steps"][0]["id"] == "confirm-first-counties"
    assert manifest["your_steps"][1]["id"] == "texas-consultant-registration"
    for flow_name in manifest["flows"]:
        flow = json.loads((base / "flows" / f"{flow_name}.json").read_text())
        assert flow["nodes"] and flow["edges"]
        for edge in flow["edges"]:
            source = next(node for node in flow["nodes"] if node["id"] == edge["source"])
            target = next(node for node in flow["nodes"] if node["id"] == edge["target"])
            if target["type"] == "command" and any(word in target["config"]["cmd"].lower() for word in ("send", "submit", "checkout", "postcard")):
                assert source["type"] == "approval"
