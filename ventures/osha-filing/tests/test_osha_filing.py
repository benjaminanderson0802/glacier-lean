from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("osha_filing", ROOT / "scripts" / "filing.py")
filing = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(filing)


def valid_intake(**changes):
    payload = {
        "establishment": {"name": "Northside Heating", "address": "1 Main St, Sampleville, IL", "industry_code": "238220", "employees": 24},
        "year": 2025,
        "injury_log": {"deaths": 0, "days_away": 0, "job_transfer": 0, "other_cases": 0, "days_away_count": 0, "job_transfer_count": 0, "other_days": 0},
        "hours_worked": 48000,
        "average_employees": 24,
        "executive_name": "Alex Example",
        "executive_title": "Owner",
        "customer_confirmed": True,
        "coverage_confirmed": True,
    }
    payload.update(changes)
    return payload


def test_generates_reviewable_300a_and_requires_customer_submission(tmp_path):
    result = filing.prepare_300a(valid_intake(), tmp_path)
    assert result["result"] == "match"
    assert result["customer_must_certify_and_submit"] is True
    assert result["submitted"] is False
    assert result["signed"] is False
    assert Path(result["form_path"]).is_file()
    form = json.loads(Path(result["form_path"]).read_text())
    assert form["establishment"] == "Northside Heating"
    assert form["total_cases"] == 0
    assert form["hours_worked"] == 48000


def test_plausibility_and_confirmation_checks_block_incomplete_intake(tmp_path):
    bad = valid_intake(hours_worked=1, customer_confirmed=False)
    result = filing.prepare_300a(bad, tmp_path)
    assert result["result"] == "uncertain — please check"
    assert result["form_path"] is None
    assert {"customer confirmation", "plausible hours and headcount"} <= set(result["please_confirm"])


def test_deadline_window_and_manifest_keep_filing_customer_controlled():
    assert filing.filing_window("2027-01-02") == "open"
    assert filing.filing_window("2027-03-03") == "closed"
    manifest = json.loads((ROOT / "venture.json").read_text())
    assert manifest["slug"] == "osha-filing"
    assert len(manifest["your_steps"]) <= 3
    flow = json.loads((ROOT / "flows" / "prepare-300a.json").read_text())
    assert any(node["type"] == "approval" for node in flow["nodes"])
    assert all("submit" not in node.get("config", {}).get("cmd", "").lower() for node in flow["nodes"])
