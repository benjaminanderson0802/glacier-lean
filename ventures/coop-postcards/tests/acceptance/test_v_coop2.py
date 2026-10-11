"""Independent co-op claim and postcard acceptance checks."""
from datetime import date, timedelta
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "coop-postcards"))

def load_workflow():
    spec = importlib.util.spec_from_file_location("acceptance_coop_workflow", ROOT / "coop-postcards/workflow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.xfail(strict=False, reason="awaiting builder V-COOP2")
def test_brand_rules_cover_five_brands_with_source_links_and_uncertainty():
    workflow = load_workflow()
    rules = getattr(workflow, "BRAND_RULES", getattr(workflow, "COOP_RULES", {}))
    for brand in ("Carrier", "Trane", "Lennox", "Rheem", "Goodman"):
        rule = rules.get(brand.lower()) or rules.get(brand)
        assert rule and rule.get("source_url", rule.get("source"))
        if not rule.get("verified", False):
            assert rule.get("status", "unverified") in {"unverified", "uncertain"}


def test_claim_deadlines_are_before_expiration_and_postcard_is_render_only(monkeypatch):
    workflow = load_workflow()
    claim_reminder_dates, check_route_card = workflow.claim_reminder_dates, workflow.check_route_card
    dates = claim_reminder_dates("2027-01-01")
    assert dates == [date(2027, 1, 1) - timedelta(days=60), date(2027, 1, 1) - timedelta(days=30)]
    # Route validation is a pure check; it cannot send or publish mail.
    result = check_route_card({})
    assert result.get("verdict") in {"fail", "uncertain"} or result.get("ready") is False


@pytest.mark.xfail(strict=False, reason="awaiting builder V-COOP2")
def test_fixture_jobber_intake_creates_claim_draft_artifacts(tmp_path):
    workflow = load_workflow()
    build = getattr(workflow, "prepare_claim_draft", None) or getattr(workflow, "generate_claim_draft", None)
    assert callable(build)
    job = {"job_id": "9001", "brand": "Carrier", "program_year": "2026", "invoice": "INV-11",
           "installed_on": "2026-04-01", "dealer_authorized": True, "preapproval_id": "PA-1"}
    result = build(job, output_dir=tmp_path)
    assert result["filing_ready"] is True
    assert result["reminders"]
    assert any(path.suffix.lower() in {".pdf", ".md", ".markdown"} for path in tmp_path.iterdir())
