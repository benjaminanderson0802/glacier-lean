import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "scripts"))
from dibbs_supply import prepare_bids  # noqa: E402

def solicitation(**overrides):
    row = {
        "solicitation_number": "SPE7M126T001A",
        "nsn": "5930-01-234-5678",
        "part_number": "SW-123",
        "description": "Electrical switch, exact approved part",
        "source_url": "https://www.dibbs.bsm.dla.mil/rfq/SPE7M126T001A",
        "open_to_all_suppliers": True,
        "electronic_part": False,
        "return_by_date": "2026-11-01",
        "quantity": 10,
        "required_fields": ["solicitation_number", "nsn", "part_number", "quantity", "unit_price", "supplier_name"],
        "quote_file": "quote.csv",
    }
    supplied = {**row, **overrides}
    if "source_url" not in overrides:
        supplied["source_url"] = f"https://www.dibbs.bsm.dla.mil/rfq/{supplied['solicitation_number']}"
    return supplied


def supplier_quote(**overrides):
    row = {
        "solicitation_number": "SPE7M126T001A",
        "part_number": "SW-123",
        "supplier_name": "Original Manufacturer",
        "supplier_type": "manufacturer",
        "authorization_evidence": "evidence/manufacturer-letter.pdf",
        "traceability_evidence": "evidence/traceability.pdf",
        "quantity": 10,
        "unit_cost": "40.00",
        "unit_bid_price": "55.00",
        "lead_time_days": 15,
    }
    return {**row, **overrides}


def write_inputs(tmp_path, solicitations, quotes):
    solicitation_path = tmp_path / "solicitations.json"
    quote_path = tmp_path / "quotes.json"
    output_path = tmp_path / "out"
    for index, quote in enumerate(quotes):
        for field in ("authorization_evidence", "traceability_evidence"):
            if quote.get(field):
                evidence = tmp_path / f"evidence-{index}-{field}.pdf"
                evidence.write_bytes(b"fixture evidence")
                quote[field] = str(evidence)
    solicitation_path.write_text(json.dumps(solicitations), encoding="utf-8")
    quote_path.write_text(json.dumps(quotes), encoding="utf-8")
    return solicitation_path, quote_path, output_path


def test_prepares_ranked_batch_with_exact_part_supplier_and_margin(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path,
        [solicitation(), solicitation(solicitation_number="SPE7M126T002B", nsn="5930-01-765-4321", part_number="SW-456", quote_file="second.csv")],
        [
            supplier_quote(),
            supplier_quote(solicitation_number="SPE7M126T002B", part_number="SW-456", supplier_name="Authorized Distributor", supplier_type="authorized_distributor", authorization_evidence="evidence/distributor-authorization.pdf", unit_cost="45", unit_bid_price="70", traceability_evidence="evidence/traceability-456.pdf"),
        ],
    )

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["result"] == "match"
    assert result["submitted"] is False
    assert [row["solicitation_number"] for row in result["ranked_bids"]] == ["SPE7M126T002B", "SPE7M126T001A"]
    assert result["ranked_bids"][0]["gross_margin_percent"] == 35.71
    assert all(row["part_number"] == "SW-456" if row["solicitation_number"] == "SPE7M126T002B" else row["part_number"] == "SW-123" for row in result["ranked_bids"])
    with (output_path / "quote.csv").open(newline="", encoding="utf-8") as stream:
        assert list(csv.DictReader(stream)) == [{
            "solicitation_number": "SPE7M126T001A", "nsn": "5930-01-234-5678", "part_number": "SW-123",
            "quantity": "10", "unit_price": "55.00", "supplier_name": "Original Manufacturer",
        }]
    with (output_path / "second.csv").open(newline="", encoding="utf-8") as stream:
        assert list(csv.DictReader(stream))[0]["supplier_name"] == "Authorized Distributor"


def test_excludes_closed_supplier_restricted_electronic_and_mismatched_parts(tmp_path):
    solicitations = [
        solicitation(solicitation_number="CLOSED", open_to_all_suppliers=False),
        solicitation(solicitation_number="ELECTRONIC", electronic_part=True),
        solicitation(solicitation_number="MISMATCH"),
    ]
    quotes = [
        supplier_quote(solicitation_number="CLOSED"),
        supplier_quote(solicitation_number="ELECTRONIC"),
        supplier_quote(solicitation_number="MISMATCH", part_number="OTHER"),
    ]
    solicitation_path, quote_path, output_path = write_inputs(tmp_path, solicitations, quotes)

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["ranked_bids"] == []
    assert {item["solicitation_number"] for item in result["excluded"]} == {"CLOSED", "ELECTRONIC"}
    assert {item["solicitation_number"] for item in result["uncertain"]} == {"MISMATCH"}
    assert not list(output_path.glob("*.csv"))


def test_missing_eligibility_authorization_or_traceability_never_becomes_bid(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path,
        [solicitation(open_to_all_suppliers=None), solicitation(solicitation_number="SPE7M126T002B", part_number="SW-456")],
        [supplier_quote(), supplier_quote(solicitation_number="SPE7M126T002B", part_number="SW-456", authorization_evidence="", traceability_evidence="")],
    )

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["ranked_bids"] == []
    assert result["result"] == "uncertain — please check"
    assert len(result["uncertain"]) == 2
    assert not list(output_path.glob("*.csv"))


def test_only_original_manufacturer_or_authorized_distributor_is_accepted(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path, [solicitation()], [supplier_quote(supplier_type="reseller")]
    )

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["ranked_bids"] == []
    assert result["uncertain"][0]["solicitation_number"] == "SPE7M126T001A"


def test_flow_and_manifest_gate_all_external_or_legal_steps(tmp_path):
    venture = ROOT.parent
    manifest = json.loads((venture / "venture.json").read_text(encoding="utf-8"))
    flow = json.loads((venture / "flows" / "dibbs-daily-prep.json").read_text(encoding="utf-8"))
    registration = json.loads((venture / "flows" / "dibbs-owner-registration.json").read_text(encoding="utf-8"))
    node_types = {node["type"] for node in flow["nodes"]}
    prompts = "\n".join(node.get("config", {}).get("prompt", "") for node in flow["nodes"] if node["type"] == "approval")

    assert manifest["slug"] == "dibbs-supply"
    assert len(manifest["your_steps"]) <= 3
    assert {"schedule", "command", "check", "approval", "note"} <= node_types
    assert "Your step:" in prompts
    assert "sign" in prompts.lower() and "submit" in prompts.lower()
    command = next(node["config"].get("cmd", "") for node in flow["nodes"] if node["id"] == "prepare")
    assert "GLACIER_PROJECT_ROOT" in command and "dibbs_supply.py" in command
    owner_steps = " ".join(step["title"] + " " + step["detail"] for step in manifest["your_steps"])
    owner_links = [link for step in manifest["your_steps"] for link in step["links"]]
    assert "SAM.gov" in owner_steps and "CAGE" in owner_steps
    assert "https://www.dibbs.bsm.dla.mil/rfq/" in owner_links
    assert "https://sam.gov/entity-registration" in owner_links
    assert "https://cage.dla.mil/" in owner_links
    assert "dibbs-owner-registration" in manifest["flows"]
    purchase = next(node for node in flow["nodes"] if node["id"] == "parts_spend_approval")
    assert purchase["type"] == "approval"
    assert "before any purchase" in purchase["config"]["prompt"].lower()
    assert any(edge["source"] == "owner_review" and edge["target"] == "parts_spend_approval" for edge in flow["edges"])
    registration_prompts = " ".join(node["config"].get("prompt", "") for node in registration["nodes"] if node["type"] == "approval")
    assert "Your step:" in registration_prompts and "sam.gov" in registration_prompts.lower() and "cage.dla.mil" in registration_prompts
    assert "manufacturer" in (venture / "README.md").read_text(encoding="utf-8").lower()


def test_daily_feed_alert_stays_visible_even_when_a_local_quote_matches(tmp_path, monkeypatch):
    from ventures.blocks import feeds
    from dibbs_supply import prepare_from_feed

    solicitation_path, quote_path, _ = write_inputs(tmp_path, [solicitation()], [supplier_quote()])
    monkeypatch.setattr(feeds, "sync", lambda source: {"rows": 1, "changed": True, "alerts": ["DIBBS discovery feed is incomplete"]})
    monkeypatch.setattr(feeds, "query", lambda source: [{
        "record_id": "SPE7M126T001A",
        "source_url": "https://www.dibbs.bsm.dla.mil/rfq/SPE7M126T001A",
        "data": {"description": "public discovery row"},
    }])

    result = prepare_from_feed(tmp_path / "drafts", solicitation_path, quote_path)

    assert result["ranked_bids"][0]["source_url"] == "https://www.dibbs.bsm.dla.mil/rfq/SPE7M126T001A"
    assert result["result"] == "uncertain — please check"
    assert result["feed_alerts"] == ["DIBBS discovery feed is incomplete"]
    assert result["submitted"] is False
    assert (tmp_path / "drafts" / "bid-sheet.json").is_file()


def test_prepares_supplier_contact_drafts_for_owner_review_without_sending(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path,
        [solicitation(business_name="Example Supply LLC", supplier_quote_due_date="2026-10-20", quote_sources=[{
            "supplier_name": "Original Manufacturer",
            "supplier_type": "manufacturer",
            "contact_email": "quotes@example.test",
            "authorization_evidence": str(tmp_path / "evidence-0-authorization_evidence.pdf"),
        }])],
        [],
    )

    (tmp_path / "evidence-0-authorization_evidence.pdf").write_bytes(b"supplier authorization")
    result = prepare_bids(solicitation_path, quote_path, output_path, as_of=__import__("datetime").date(2026, 10, 10))

    assert result["quote_requests"][0]["to"] == "quotes@example.test"
    assert "SPE7M126T001A" in result["quote_requests"][0]["subject"]
    assert "SW-123" in result["quote_requests"][0]["body"]
    assert result["quote_requests"][0]["sent"] is False
    assert (output_path / "quote-request-drafts.json").is_file()


def test_unprofitable_quote_is_not_written_as_a_bid(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path, [solicitation()], [supplier_quote(unit_cost="40", unit_bid_price="39")]
    )

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["ranked_bids"] == []
    assert "below unit cost" in " ".join(result["uncertain"][0]["reasons"])
    assert not list(output_path.glob("*.csv"))


def test_quote_request_draft_requires_open_non_electronic_current_solicitation(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path,
        [solicitation(open_to_all_suppliers=None, electronic_part=True, business_name="Example Supply LLC", supplier_quote_due_date="2026-10-20", quote_sources=[{
            "supplier_name": "Original Manufacturer", "supplier_type": "manufacturer",
            "contact_email": "quotes@example.test", "authorization_evidence": str(tmp_path / "evidence-0-authorization_evidence.pdf"),
        }])],
        [],
    )
    (tmp_path / "evidence-0-authorization_evidence.pdf").write_bytes(b"supplier authorization")

    result = prepare_bids(solicitation_path, quote_path, output_path, as_of=__import__("datetime").date(2026, 10, 10))

    assert result["quote_requests"] == []
    assert "eligibility" in " ".join(result["quote_request_uncertain"][0]["reasons"])
    assert "non-electronic" in " ".join(result["quote_request_uncertain"][0]["reasons"])


def test_flow_only_opens_owner_approval_when_there_are_draft_actions(tmp_path, monkeypatch, capsys):
    import dibbs_supply

    paths = ["prepare", "--solicitations", str(tmp_path / "s.json"), "--quotes", str(tmp_path / "q.json"), "--output", str(tmp_path / "out")]
    monkeypatch.setattr(dibbs_supply, "prepare_bids", lambda *args: {"result": "uncertain — please check", "ranked_bids": [{"solicitation_number": "SPE7M126T001A"}], "quote_requests": []})
    assert dibbs_supply.main(paths) == 0
    capsys.readouterr()
    monkeypatch.setattr(dibbs_supply, "prepare_bids", lambda *args: {"result": "no match found in DLA DIBBS and supplier quotes as of 2026-10-10", "ranked_bids": [], "quote_requests": []})
    assert dibbs_supply.main(paths) == 2


def test_bid_requires_a_source_link_to_the_exact_official_solicitation(tmp_path):
    solicitation_path, quote_path, output_path = write_inputs(
        tmp_path, [solicitation(source_url="https://example.test/SPE7M126T001A")], [supplier_quote()]
    )

    result = prepare_bids(solicitation_path, quote_path, output_path)

    assert result["ranked_bids"] == []
    assert "official DIBBS solicitation link" in " ".join(result["uncertain"][0]["reasons"])
