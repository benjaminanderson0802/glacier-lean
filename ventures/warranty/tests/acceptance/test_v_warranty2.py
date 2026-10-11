"""Independent acceptance checks for Jobber warranty intake and owner drafts."""
import json
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "blocks" / "connectors"))
sys.path.insert(0, str(ROOT / "warranty"))

def load_warranty():
    spec = importlib.util.spec_from_file_location("acceptance_warranty", ROOT / "warranty/scripts/warranty.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unverified_brand_serial_patterns_remain_uncertain():
    evaluate_install = load_warranty().evaluate_install
    record = {"unit_id": "9001", "brand": "trane", "completed": True, "installed_on": "2026-04-01",
              "model_reading": "XR-15", "serial_reading": "SN-EXAMPLE-41", "model_confirmation": "XR-15",
              "serial_confirmation": "SN-EXAMPLE-41", "serial_format_validated": True,
              "homeowner_name": "Rae Example", "homeowner_email": "rae@example.test"}
    result = evaluate_install(record, as_of=date(2026, 4, 2))
    assert result["result"].startswith("uncertain")
    assert result["registration_action"] == "hold"
    assert result["portal_automation_allowed"] is False


def test_jobber_graphql_fixture_maps_completed_job_to_homeowner_draft():
    from ventures.blocks.connectors import JobberClient
    warranty = load_warranty()
    fixture = json.loads((Path(__file__).parent / "fixtures/jobber-jobs-2026-04-16.json").read_text(encoding="utf-8"))
    client = JobberClient()
    jobs = client._normalize_jobs(fixture) if hasattr(client, "_normalize_jobs") else client._parse_jobs(fixture)
    assert jobs and jobs[0]["job_id"] == "gid://jobber/Job/9001"
    units = warranty.prepare_batch(jobs, as_of=date(2026, 4, 2))
    assert units["units"]
    assert any("email" in str(unit).lower() or "draft" in str(unit).lower() for unit in units["units"])


def test_read_only_owner_check_never_prints_secret(monkeypatch, capsys):
    warranty = load_warranty()
    monkeypatch.setattr(warranty, "read_jobber_jobs", lambda: [{"job_id": "test", "completed": True}])
    code = warranty.main(["jobber-preview"])
    output = capsys.readouterr().out
    assert code == 0
    assert "access_token" not in output and "client_secret" not in output
