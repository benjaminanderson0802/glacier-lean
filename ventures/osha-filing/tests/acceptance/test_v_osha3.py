"""Independent OSHA 300A and filing-window acceptance checks."""
import json
import sys
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "osha-filing"))

def load_filing():
    spec = importlib.util.spec_from_file_location("acceptance_osha_filing", ROOT / "osha-filing/scripts/filing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_filing_windows_separate_posting_and_submission_dates():
    filing_window = load_filing().filing_window
    assert filing_window("2026-01-01") == "upcoming"
    assert filing_window("2026-01-02") == "open"
    assert filing_window("2026-03-02") == "open"
    assert filing_window("2026-03-03") == "closed"


def test_300a_preparation_is_unsigned_unsubmitted_and_requires_customer_certification(tmp_path):
    prepare_300a = load_filing().prepare_300a
    fixture = Path(__file__).parent / "fixtures/injury-log.csv"
    assert fixture.is_file()
    # Public preparation interface accepts the normalized JSON row model; CSV conversion belongs to the workflow.
    data = {"establishment": {"name": "Example HVAC", "address": "1 Main St", "industry_code": "238220", "employees": 20},
            "year": 2025, "average_employees": 12, "hours_worked": 24000,
            "injury_log": {"deaths": 0, "days_away": 0, "job_transfer": 0, "other_cases": 0},
            "coverage_confirmed": True, "customer_confirmed": True,
            "executive_name": "A. Owner", "executive_title": "President"}
    result = prepare_300a(data, tmp_path, as_of="2026-02-15")
    assert result["customer_must_certify_and_submit"] is True
    assert result["signed"] is False and result["submitted"] is False
    assert Path(result["form_path"]).is_file()


def test_300a_template_is_provided():
    paths = list(Path(__file__).resolve().parents[2].glob("**/*injury*log*.csv"))
    assert paths, "customer injury-log CSV template is required"


def test_injury_log_csv_runs_through_to_unsigned_worksheet(tmp_path):
    import pytest
    from pathlib import Path
    from scripts import filing
    prepare_from_csv = getattr(filing, "prepare_from_injury_log_csv", None)
    assert callable(prepare_from_csv)
    fixture = Path(__file__).parent / "fixtures/injury-log.csv"
    result = prepare_from_csv(fixture, tmp_path, as_of="2026-02-15")
    assert result["signed"] is False and result["submitted"] is False
    assert result["customer_must_certify_and_submit"] is True
