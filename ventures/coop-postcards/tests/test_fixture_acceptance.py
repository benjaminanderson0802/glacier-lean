"""End-to-end acceptance for the offline Jobber fixture claim draft."""
from __future__ import annotations

import json
import importlib.util
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VENTURE = ROOT / "ventures/coop-postcards"
FIXTURE = ROOT / "ventures/coop-postcards/fixtures/jobber_completed_job.json"


def _load_cli(name: str):
    path = VENTURE / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"coop_postcards_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_completed_job_fixture_creates_local_claim_draft_only(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Completed jobs make reviewable drafts; this fixture causes no egress."""
    def reject_network(*_args, **_kwargs):
        raise AssertionError("fixture processing must not make an external request")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)

    generate_claim_drafts = _load_cli("generate_claim_drafts")
    run_approved_claim = _load_cli("run_approved_claim")
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier-home"))
    output_dir = tmp_path / "claims"
    assert generate_claim_drafts.main(
        ["--fixture", str(FIXTURE), "--output-dir", str(output_dir)]
    ) == 0
    summary = json.loads(capsys.readouterr().out)

    assert summary["drafts_created"] == 1
    assert summary["external_actions"] == "none"
    assert len(summary["drafts"]) == 1
    draft_summary = summary["drafts"][0]
    assert draft_summary["job_number"] == "2048"
    assert draft_summary["rule_status"] == "unverified"
    assert draft_summary["filing_ready"] is False
    assert draft_summary["deadline_status"] == "scheduled from confirmed expiry"

    records = list(output_dir.glob("*.json"))
    markdown_files = list(output_dir.glob("*.md"))
    pdf_files = list(output_dir.glob("*.pdf"))
    assert len(records) == len(markdown_files) == len(pdf_files) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    markdown = markdown_files[0].read_text(encoding="utf-8")

    # The ACTIVE fixture job is ignored, and no homeowner identity is needed.
    assert record["job_id"] == "fixture-job-2026-001"
    assert record["job_number"] == "2048"
    assert record["dealer_label"] == "Fixture HVAC"
    assert record["rule_status"] == "unverified"
    assert record["brand_rule"]["rule_status"] == "unverified"
    assert record["brand_rule"]["source_url"].startswith("https://")
    assert record["brand_rule"]["must_confirm_with_brand"]
    assert {item["key"] for item in record["evidence_checklist"]} >= {
        "dealer_authorization",
        "ad_proof",
        "itemized_invoice",
        "proof_of_payment",
    }
    assert record["expires_on"] == "2026-12-31"
    assert record["reminder_dates"] == ["2026-11-01", "2026-12-01"]
    assert "fixture-job-open-002" not in json.dumps(record)
    assert "homeowner" not in json.dumps(record).casefold()
    assert "Rule status: unverified" in markdown
    assert "Evidence checklist" in markdown
    assert "Reminder dates: 2026-11-01, 2026-12-01" in markdown
    assert "does not submit it" in markdown
    assert pdf_files[0].read_bytes().startswith(b"%PDF-")

    # The public legacy filing entry point is a local owner-action notice only.
    assert run_approved_claim.main(["--approval", "fixture-review"]) == 0
    filing_response = json.loads(capsys.readouterr().out)
    assert filing_response["status"] == "owner_action_required"
    assert filing_response["external_actions"] == "none"
    assert "no claim was filed" in filing_response["detail"]
