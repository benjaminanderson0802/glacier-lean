from __future__ import annotations

from datetime import date

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


def test_missing_photo_yields_a_request_draft_only_if_technician_opted_in():
    opted_in = evaluate_install(record(model_reading="", model_confirmation="", serial_reading="", serial_confirmation="", technician_opted_in=True), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)
    opted_out = evaluate_install(record(model_reading="", model_confirmation="", serial_reading="", serial_confirmation="", technician_opted_in=False), as_of=date(2026, 6, 10), brand_rules=TEST_RULES)

    assert opted_in["photo_request_draft"]
    assert opted_in["photo_request_draft"]["sent"] is False
    assert opted_out["photo_request_draft"] is None
