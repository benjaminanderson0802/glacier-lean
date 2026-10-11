import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from dibbs_supply import prepare_bids  # noqa: E402


def _record_digest(record):
    bound = {key: value for key, value in record.items() if key != "owner_confirmation"}
    encoded = json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _confirmed_record(record, evidence_path, acquired_at):
    content = evidence_path.read_bytes()
    record["source_provenance"] = {
        "path": str(evidence_path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "acquired_at": acquired_at,
    }
    record["superseded"] = False
    record["owner_confirmation"] = {
        "confirmed_by": "owner",
        "confirmed_at": "2026-10-10",
    }
    record["owner_confirmation"]["record_sha256"] = _record_digest(record)
    return record


def _inputs(tmp_path):
    detail_path = tmp_path / "dibbs-detail.html"
    quote_path = tmp_path / "supplier-quote.pdf"
    detail_path.write_bytes(b"synthetic DIBBS detail revision A")
    quote_path.write_bytes(b"synthetic supplier quote revision R1")
    solicitation = {
        "solicitation_number": "SPE7M126T001A",
        "nsn": "5930-01-234-5678",
        "part_number": "P-100",
        "source_url": "https://www.dibbs.bsm.dla.mil/rfq/SPE7M126T001A",
        "open_to_all_suppliers": True,
        "electronic_part": False,
        "return_by_date": "2026-11-01",
        "quantity": 10,
        "required_fields": ["solicitation_number", "nsn", "part_number", "quantity", "unit_price", "supplier_name"],
        "quote_file": "quote.csv",
    }
    quote = {
        "solicitation_number": "SPE7M126T001A",
        "part_number": "P-100",
        "supplier_name": "S-1",
        "supplier_type": "manufacturer",
        "authorization_evidence": str(detail_path),
        "traceability_evidence": str(quote_path),
        "quantity": 10,
        "unit_cost": "40.00",
        "unit_bid_price": "55.00",
        "quote_revision": "R1",
    }
    _confirmed_record(solicitation, detail_path, "2026-10-09")
    _confirmed_record(quote, quote_path, "2026-10-10")
    solicitation_file = tmp_path / "solicitations.json"
    quote_file = tmp_path / "quotes.json"
    solicitation_file.write_text(json.dumps([solicitation]), encoding="utf-8")
    quote_file.write_text(json.dumps([quote]), encoding="utf-8")
    return solicitation, quote, solicitation_file, quote_file


def test_confirmed_records_rank_with_source_provenance_and_unsigned_trace(tmp_path):
    solicitation, quote, solicitation_file, quote_file = _inputs(tmp_path)

    result = prepare_bids(solicitation_file, quote_file, tmp_path / "out", as_of=date(2026, 10, 10))

    assert len(result["ranked_bids"]) == 1
    row = result["ranked_bids"][0]
    assert row["input_provenance"]["solicitation"]["source_sha256"] == solicitation["source_provenance"]["sha256"]
    assert row["input_provenance"]["solicitation"]["acquired_at"] == "2026-10-09"
    assert row["input_provenance"]["solicitation"]["record_sha256"] == solicitation["owner_confirmation"]["record_sha256"]
    assert row["input_provenance"]["quote"]["source_sha256"] == quote["source_provenance"]["sha256"]
    assert row["input_provenance"]["quote"]["acquired_at"] == "2026-10-10"
    assert row["input_provenance"]["quote"]["record_sha256"] == quote["owner_confirmation"]["record_sha256"]
    with (tmp_path / "out" / "quote.csv").open(newline="", encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 1
    provenance = json.loads((tmp_path / "out" / "quote-provenance.json").read_text(encoding="utf-8"))
    assert provenance["quote.csv"][0]["solicitation_record_sha256"] == solicitation["owner_confirmation"]["record_sha256"]
    assert provenance["quote.csv"][0]["quote_record_sha256"] == quote["owner_confirmation"]["record_sha256"]
    assert result["submitted"] is False


@pytest.mark.parametrize(
    ("record_name", "field", "value"),
    [
        ("solicitation", "part_number", "P-200"),
        ("solicitation", "quantity", 11),
        ("quote", "supplier_name", "S-2"),
        ("quote", "quote_revision", "R2"),
    ],
)
def test_changed_confirmed_fields_do_not_reuse_prior_confirmation(tmp_path, record_name, field, value):
    solicitation, quote, solicitation_file, quote_file = _inputs(tmp_path)
    target = solicitation if record_name == "solicitation" else quote
    target[field] = value
    solicitation_file.write_text(json.dumps([solicitation]), encoding="utf-8")
    quote_file.write_text(json.dumps([quote]), encoding="utf-8")

    result = prepare_bids(solicitation_file, quote_file, tmp_path / "out", as_of=date(2026, 10, 10))

    assert result["ranked_bids"] == []
    assert result["result"] == "uncertain — please check"
    assert not (tmp_path / "out" / "quote.csv").exists()


def test_changed_source_bytes_are_withheld(tmp_path):
    solicitation, quote, solicitation_file, quote_file = _inputs(tmp_path)
    Path(solicitation["source_provenance"]["path"]).write_bytes(b"changed DIBBS detail")
    solicitation_file.write_text(json.dumps([solicitation]), encoding="utf-8")
    quote_file.write_text(json.dumps([quote]), encoding="utf-8")

    result = prepare_bids(solicitation_file, quote_file, tmp_path / "out", as_of=date(2026, 10, 10))

    assert result["ranked_bids"] == []
    assert not (tmp_path / "out" / "quote.csv").exists()


def test_superseded_quote_is_withheld_even_with_a_fresh_confirmation(tmp_path):
    solicitation, quote, solicitation_file, quote_file = _inputs(tmp_path)
    quote["superseded"] = True
    quote["owner_confirmation"]["record_sha256"] = _record_digest(quote)
    solicitation_file.write_text(json.dumps([solicitation]), encoding="utf-8")
    quote_file.write_text(json.dumps([quote]), encoding="utf-8")

    result = prepare_bids(solicitation_file, quote_file, tmp_path / "out", as_of=date(2026, 10, 10))

    assert result["ranked_bids"] == []
    assert not (tmp_path / "out" / "quote.csv").exists()


def test_missing_provenance_or_confirmation_withholds_row(tmp_path):
    solicitation, quote, solicitation_file, quote_file = _inputs(tmp_path)
    del solicitation["owner_confirmation"]
    solicitation_file.write_text(json.dumps([solicitation]), encoding="utf-8")
    quote_file.write_text(json.dumps([quote]), encoding="utf-8")

    result = prepare_bids(solicitation_file, quote_file, tmp_path / "out", as_of=date(2026, 10, 10))

    assert result["ranked_bids"] == []
    assert not (tmp_path / "out" / "quote.csv").exists()
