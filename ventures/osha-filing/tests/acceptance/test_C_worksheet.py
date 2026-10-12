"""Independent acceptance checks for unsigned OSHA CSV worksheets.

All input is synthetic. These checks cover value traceability and the customer
handoff; they do not determine coverage or authorize a filing.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
OSHA_SCRIPT = REPO_ROOT / "ventures" / "osha-filing" / "scripts" / "osha_filing.py"
SPEC = importlib.util.spec_from_file_location("c_worksheet_osha_filing", OSHA_SCRIPT)
assert SPEC and SPEC.loader
OSHA = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(REPO_ROOT))
SPEC.loader.exec_module(OSHA)


FIELDS = [
    "case_id", "year", "establishment_name", "establishment_id", "industry_code",
    "establishment_address", "establishment_city", "establishment_state", "establishment_zip",
    "average_employees", "total_hours_worked", "case_type", "days_away",
    "job_transfer_or_restriction_days", "executive_name", "executive_title", "source_date",
    "private_note",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sample_row(**overrides: str) -> dict[str, str]:
    row = {
        "case_id": "SYN-001",
        "year": "2025",
        "establishment_name": "Synthetic Machine Works",
        "establishment_id": "000012345",
        "industry_code": "332710",
        "establishment_address": "10 Sample Road",
        "establishment_city": "Testville",
        "establishment_state": "IL",
        "establishment_zip": "60000",
        "average_employees": "25",
        "total_hours_worked": "48000",
        "case_type": "days_away",
        "days_away": "3",
        "job_transfer_or_restriction_days": "0",
        "executive_name": "Synthetic Executive",
        "executive_title": "Owner",
        "source_date": "2025-01-14",
        "private_note": "DO-NOT-MAP-THIS-SENTINEL",
    }
    row.update(overrides)
    return row


def test_csv_values_reach_unsigned_worksheet_with_source_row_and_date_provenance(tmp_path):
    source = tmp_path / "synthetic-injury-log.csv"
    write_csv(source, [
        sample_row(),
        sample_row(
            case_id="SYN-002", case_type="job_transfer_or_restriction", days_away="0",
            job_transfer_or_restriction_days="5", source_date="2025-02-03",
        ),
    ])
    fields = OSHA.load_customer_csv(source)
    packet = OSHA.build_300a_packet(fields)
    worksheet = packet["html"]

    # Only supported worksheet values are mapped; category cases and day counts
    # remain distinct and totals are derived from the source rows.
    assert fields["year"] == "2025"
    assert fields["establishment_name"] == "Synthetic Machine Works"
    assert fields["establishment_id"] == "000012345"
    assert fields["total_cases"] == 2
    assert fields["cases_with_days_away"] == 1
    assert fields["cases_with_job_transfer_or_restriction"] == 1
    assert fields["days_away"] == 3
    assert fields["job_transfer_or_restriction_days"] == 5
    assert "DO-NOT-MAP-THIS-SENTINEL" not in worksheet

    # The review copy must let a reviewer trace each supplied case back to its
    # CSV line and supplied date, rather than only showing aggregated totals.
    assert "synthetic-injury-log.csv" in worksheet
    assert "CSV row 2" in worksheet and "2025-01-14" in worksheet
    assert "CSV row 3" in worksheet and "2025-02-03" in worksheet
    assert packet["result"] == "match"
    assert packet["signature"] == "customer_signature_required"
    assert packet["submission"] == "customer_submits_in_osha_ita"
    assert "Signature: ____________________________________" in worksheet
    assert "Date: ______________" in worksheet


def test_missing_values_stay_explicit_and_the_review_is_uncertain(tmp_path):
    source = tmp_path / "synthetic-incomplete-injury-log.csv"
    write_csv(source, [sample_row(
        average_employees="", total_hours_worked="", establishment_zip="",
    )])
    fields = OSHA.load_customer_csv(source)
    packet = OSHA.build_300a_packet(fields)

    assert packet["result"] == "uncertain — please check"
    assert "Customer confirmation needed" in packet["html"]
    assert "DO-NOT-MAP-THIS-SENTINEL" not in packet["html"]
    assert "Customer confirmation required" in packet["html"]


def test_csv_worksheet_never_signs_submits_or_makes_external_requests(tmp_path, monkeypatch):
    source = tmp_path / "synthetic-injury-log.csv"
    write_csv(source, [sample_row()])

    def forbidden_request(*_args, **_kwargs):
        pytest.fail("worksheet preparation must not make an external request")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_request)
    fields = OSHA.load_customer_csv(source)
    packet = OSHA.build_300a_packet(fields)

    assert packet["signature"] == "customer_signature_required"
    assert packet["submission"] == "customer_submits_in_osha_ita"
    assert "Glacier does not certify or submit" in packet["html"]
    assert "Signature: ____________________________________" in packet["html"]
    assert "Date: ______________" in packet["html"]
