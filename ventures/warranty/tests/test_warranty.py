from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from ventures.warranty.scripts.warranty import evaluate_install, prepare_batch

TEST_RULES = {
    brand: {"window_days": 90 if brand == "carrier" else 60, "serial_pattern": r"[A-Z0-9]{10}", "source": "https://example.test/test-fixture"}
    for brand in ("trane", "goodman", "daikin", "lennox", "carrier")
}


def record(**overrides):
    value = {
        "job_id": "job-101",
        "completed": True,
        "brand": "trane",
        "model_reading": "XV20I",
        "model_confirmation": "XV20I",
        "serial_reading": "1234567890",
        "serial_confirmation": "1234567890",
        "serial_format_validated": True,
        "installed_on": "2026-06-01",
        "region": "TX",
        "homeowner_name": "Example Homeowner",
        "homeowner_email": "homeowner@example.test",
        "technician_opted_in": False,
    }
    value.update(overrides)
    return value


def test_matching_confirmed_record_gets_brand_deadline_and_safe_result():
    result = evaluate_install(record(), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert result["result"] == "match"
    assert result["registration_deadline"] == "2026-07-31"
    assert result["days_remaining"] == 51
    assert result["registration_action"] == "owner_check_required"


@pytest.mark.parametrize(
    ("brand", "region", "installed_on", "should_skip"),
    [
        ("trane", "CA", "2026-05-01", True),
        ("carrier", "QC", "2026-05-01", True),
        ("lennox", "FL", "2026-01-01", True),
        ("lennox", "GA", "2025-12-31", False),
        ("lennox", "GA", "2026-01-01", True),
    ],
)
def test_registration_exceptions_follow_spec(brand, region, installed_on, should_skip):
    result = evaluate_install(record(brand=brand, region=region, installed_on=installed_on), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert (result["result"] == "no match found in registration-required regions as of 2026-06-10") is should_skip
    assert result["registration_action"] == ("skip" if should_skip else "owner_check_required")


def test_carrier_uses_90_day_window_and_deadline_alerts_within_ten_days():
    result = evaluate_install(record(brand="carrier", installed_on="2026-06-01"), as_of=date(2026, 8, 22), brand_rules=TEST_RULES)

    assert result["registration_deadline"] == "2026-08-30"
    assert result["days_remaining"] == 8
    assert result["deadline_alert"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"model_confirmation": "XV18I"},
        {"serial_confirmation": "9999999999"},
        {"serial_format_validated": False},
        {"brand": "unknown brand"},
        {"completed": False},
    ],
)
def test_unconfirmed_or_unrecognized_data_is_uncertain(changes):
    result = evaluate_install(record(**changes), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "hold"


def test_daikin_is_never_automated_and_brand_submit_is_not_called():
    result = evaluate_install(record(brand="daikin"), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "owner_check_required"
    assert result["portal_automation_allowed"] is False


def test_duplicate_units_are_not_prepared_twice():
    units = [record(), record(job_id="job-101")]

    result = prepare_batch(units, as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert len(result["units"]) == 1
    assert result["duplicates"] == ["1234567890"]


def test_manifest_exposes_jobber_and_brand_fallback_prerequisites():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "venture.json").read_text(encoding="utf-8"))
    setup = next(step for step in manifest["your_steps"] if step["id"] == "jobber-setup")
    terms = next(step for step in manifest["your_steps"] if step["id"] == "brand-portal-terms")
    launch = next(step for step in manifest["your_steps"] if step["id"] == "launch-and-email-review")

    assert "jobber_client_id" in setup["detail"]
    assert "five eligible test accounts" in setup["detail"]
    assert "reader and deadline blocks" in setup["detail"]
    assert "Human fallback" in terms["detail"]
    assert "uncertain — please check" in terms["detail"]
    assert "first 20 generated homeowner email drafts" in launch["detail"]


def test_unverified_brand_serial_patterns_remain_disabled():
    from ventures.warranty.scripts.warranty import BRAND_RULES

    assert all(rule["serial_pattern"] is None for rule in BRAND_RULES.values())


def test_missing_photo_yields_a_request_draft_only_if_technician_opted_in():
    opted_in = evaluate_install(record(model_reading="", model_confirmation="", serial_reading="", serial_confirmation="", technician_opted_in=True), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)
    opted_out = evaluate_install(record(model_reading="", model_confirmation="", serial_reading="", serial_confirmation="", technician_opted_in=False), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert opted_in["photo_request_draft"]
    assert opted_in["photo_request_draft"]["sent"] is False
    assert opted_out["photo_request_draft"] is None


def test_jobber_response_flows_into_registration_queue_and_unsent_homeowner_draft():
    from ventures.warranty.scripts.warranty import build_jobber_loop

    fixture = Path(__file__).resolve().parents[3] / "ventures" / "blocks" / "connectors" / "fixtures" / "jobber" / "warranty_jobs_page.json"
    job = json.loads(fixture.read_text(encoding="utf-8"))["data"]["jobs"]["nodes"][0]

    result = build_jobber_loop([job], as_of=date(2026, 6, 15))

    assert len(result["registration_queue"]) == 1
    queued = result["registration_queue"][0]
    assert queued["job_id"] == job["id"]
    assert queued["registration_deadline"] == "2026-06-18"
    assert queued["days_remaining"] == 3
    assert queued["deadline_alert"] is True
    assert queued["result"] == "uncertain — please check"
    assert "serial format is not verified" in queued["reason"]
    assert len(result["homeowner_email_drafts"]) == 1
    draft = result["homeowner_email_drafts"][0]
    assert draft["to"] == "maya@example.test"
    assert draft["sent"] is False
    assert "not registered" in draft["body"].lower()
    assert "June 18, 2026" in draft["body"]


def test_lennox_florida_change_window_flows_to_queue_and_homeowner_draft():
    from ventures.warranty.scripts.warranty import build_jobber_loop

    fixture = Path(__file__).resolve().parents[3] / "ventures" / "blocks" / "connectors" / "fixtures" / "jobber" / "warranty_jobs_page.json"
    job = deepcopy(json.loads(fixture.read_text(encoding="utf-8"))["data"]["jobs"]["nodes"][0])
    job["customFields"][0]["valueText"] = "Lennox"
    job["customFields"][3]["valueText"] = "2026-01-01"
    job["property"]["address"]["province"] = "FL"

    result = build_jobber_loop([job], as_of=date(2026, 2, 1))

    queued = result["registration_queue"][0]
    source_url = "https://www.lennox.com/residential/owners/register-and-review/product-registration/index"
    assert queued["registration_deadline"] == "2026-03-02"
    assert queued["result"] == "uncertain — please check"
    assert queued["registration_action"] == "hold"
    assert queued["registration_window"]["label"] == "Florida"
    assert queued["registration_source_url"] == source_url
    assert "coverage-change window" in queued["registration_window"]["window_type"]

    draft = result["homeowner_email_drafts"][0]
    assert draft["sent"] is False
    assert "Florida warranty guidance" in draft["body"]
    assert "March 2, 2026" in draft["body"]
    assert source_url in draft["body"]


def test_jobber_preview_persists_local_deadline_input_for_daily_flow(tmp_path, monkeypatch, capsys):
    from ventures.warranty.scripts import warranty

    fixture = Path(__file__).resolve().parents[3] / "ventures" / "blocks" / "connectors" / "fixtures" / "jobber" / "warranty_jobs_page.json"
    jobs = json.loads(fixture.read_text(encoding="utf-8"))["data"]["jobs"]["nodes"]
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(warranty, "read_jobber_jobs", lambda: jobs)

    assert warranty.main(["jobber-preview", "--as-of", "2026-06-15"]) == 0
    intake = json.loads((tmp_path / "ventures" / "warranty" / "pending-units.json").read_text(encoding="utf-8"))
    assert len(intake["units"]) == 1
    capsys.readouterr()
    assert warranty.main(["deadlines", "--as-of", "2026-06-15"]) == 0
    daily = json.loads(capsys.readouterr().out)
    assert len(daily["alerts"]) == 1
    assert daily["alerts"][0]["registration_deadline"] == "2026-06-18"


def test_jobber_completion_timestamp_is_not_substituted_for_install_date():
    from ventures.warranty.scripts.warranty import build_jobber_loop

    job = {
        "id": "job-missing-install-date",
        "jobStatus": "COMPLETED",
        "completedAt": "2026-03-20T15:30:00-05:00",
        "client": {"name": "Maya Rivera", "email": "maya@example.test"},
        "customFields": [
            {"__typename": "CustomFieldText", "label": "Brand", "valueText": "Carrier"},
            {"__typename": "CustomFieldText", "label": "Model", "valueText": "Infinity 24"},
            {"__typename": "CustomFieldText", "label": "Serial", "valueText": "ABC123456789"},
        ],
    }

    result = build_jobber_loop([job], as_of=date(2026, 6, 15))

    assert result["registration_queue"][0].get("registration_deadline") is None
    assert result["registration_queue"][0]["result"] == "uncertain — please check"
