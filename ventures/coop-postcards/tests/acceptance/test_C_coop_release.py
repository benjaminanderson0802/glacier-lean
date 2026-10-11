"""Independent fail-closed checks for local co-op claim release drafts.

Acceptance: for drafts missing ad proof, payment proof, or confirmed current
program terms, preserve the Jobber job and source links in complete local
Markdown/PDF/JSON artifacts, expose the missing proof/terms, keep filing_ready
false, and report no external action.
"""
from __future__ import annotations

import copy
import json
import socket
import sys
import zlib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
VENTURE = ROOT / "ventures/coop-postcards"
FIXTURE = VENTURE / "fixtures/jobber_completed_job.json"


def _pdf_text(path: Path) -> str:
    """Decode this venture's standard-library PDF text stream for assertions."""
    data = path.read_bytes()
    assert data.startswith(b"%PDF-")
    stream = data.split(b"stream\n", 1)[1].split(b"\nendstream", 1)[0]
    return zlib.decompress(stream).decode("latin-1")


@pytest.mark.parametrize(
    ("gap", "confirmed_expiry"),
    [
        ("ad_proof", True),
        ("proof_of_payment", True),
        ("current_program_terms", False),
    ],
)
def test_incomplete_claim_packet_stays_review_only_with_all_local_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    gap: str, confirmed_expiry: bool,
) -> None:
    """Missing evidence or terms must never yield a filing-ready claim."""
    def reject_network(*_args, **_kwargs):
        raise AssertionError("local claim draft generation must not make a network request")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier-home"))

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)
    job = payload["jobs"][0]
    details = payload["details_by_job_id"][job["id"]]
    details["evidence"] = ["itemized_invoice", "ad_proof", "proof_of_payment"]
    if gap in details["evidence"]:
        details["evidence"].remove(gap)
    if not confirmed_expiry:
        details.pop("expires_on", None)
    fixture = tmp_path / f"jobber-{gap}.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")
    output_dir = tmp_path / f"drafts-{gap}"

    script_path = VENTURE / "scripts/generate_claim_drafts.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("independent_coop_release_cli", script_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(VENTURE))
    try:
        spec.loader.exec_module(cli)
        assert cli.main(["--fixture", str(fixture), "--output-dir", str(output_dir)]) == 0
    finally:
        sys.path.remove(str(VENTURE))

    summary = json.loads(capsys.readouterr().out)
    assert summary["external_actions"] == "none"
    assert summary["drafts_created"] == 1
    assert summary["drafts"][0]["filing_ready"] is False
    assert summary["drafts"][0]["job_number"] == "2048"

    records = list(output_dir.glob("*.json"))
    markdown_files = list(output_dir.glob("*.md"))
    pdf_files = list(output_dir.glob("*.pdf"))
    assert len(records) == len(markdown_files) == len(pdf_files) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    markdown = markdown_files[0].read_text(encoding="utf-8")
    pdf_text = _pdf_text(pdf_files[0])

    source = job["jobberWebUri"]
    assert record["job_id"] == job["id"]
    assert record["job_number"] == str(job["jobNumber"])
    assert record["job_source"] == source
    assert source in markdown and source in pdf_text
    assert "2048" in markdown and "2048" in pdf_text
    assert record["filing_ready"] is False
    assert record["external_action"] == "owner only; no filing performed"

    if gap in {"ad_proof", "proof_of_payment"}:
        missing = next(item for item in record["evidence_checklist"] if item["key"] == gap)
        assert missing["present"] is False
        assert missing["label"] in markdown
        assert missing["label"] in pdf_text
    else:
        assert record["expires_on"] is None
        assert record["deadline_status"] == "pending confirmation of current program expiry"
        assert record["reminder_dates"] == []
        assert "Pending confirmation of current program expiry" in markdown
        assert "Pending confirmation of current program expiry" in pdf_text

    assert record["rule_status"] == "unverified"
    assert record["brand_rule"]["source_url"] in markdown
    assert record["brand_rule"]["source_url"] in pdf_text
    assert "unverified until the owner confirms the current dealer program terms" in markdown
    assert "Rule status: unverified" in pdf_text
    assert "current program year and expiry" in " ".join(record["brand_rule"]["must_confirm_with_brand"])
