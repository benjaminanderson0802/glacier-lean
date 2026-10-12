"""Independent, source-grounded warranty decision cases.

The cited manufacturer pages describe registration policy and possible coverage
terms. They do not establish eligibility for the particular synthetic units
below. All records use unreadable plate evidence and must stay held.
Reviewed 2026-10-11; source URLs are in SOURCE_CASES and locally frozen in
evidence/backlog2/C-WARRANTY-RULES-TESTER/source-review-2026-10-11.md.
"""
from __future__ import annotations

from datetime import date

import pytest

from ventures.warranty.scripts.warranty import BRAND_GUIDANCE, BRAND_RULES, evaluate_install


AS_OF = date(2026, 2, 1)
INSTALLED = "2026-01-01"

# These are official brand pages and the exact policy facts they support. The
# dates are calculated from the installation date above; they are not claims
# that any particular unit qualifies for the advertised coverage.
SOURCE_CASES = [
    pytest.param(
        "Carrier", "carrier-bryant", 90, "2026-04-01",
        "https://www.carrier.com/us/en/residential/homeowner-resources/warranty/",
        id="carrier-consumer-choice-90-days",
    ),
    pytest.param(
        "Trane", "trane-american-standard", 60, "2026-03-02",
        "https://www.trane.com/residential/en/resources/warranty-and-registration/",
        id="trane-registered-warranty-60-days",
    ),
    pytest.param(
        "Goodman", "goodman-amana", 60, "2026-03-02",
        "https://www.goodmanmfg.com/resources/hvac-learning-center",
        id="goodman-qualified-coverage-60-days",
    ),
    pytest.param(
        "Amana", "goodman-amana", 60, "2026-03-02",
        "https://www.amana-hac.com/support/standard-warranty",
        id="amana-family-rule-stays-conditional",
    ),
    pytest.param(
        "Lennox", "lennox", 60, "2026-03-02",
        "https://www.lennox.com/residential/owners/register-and-review/product-registration/index",
        id="lennox-eligible-jurisdiction-60-days",
    ),
    pytest.param(
        "Daikin", "daikin", 60, "2026-03-02",
        "https://daikincomfort.com/products/heating-cooling/whole-home-systems/air-conditioners/dx4sq",
        id="daikin-dx4sq-policy-window-does-not-prove-eligibility",
    ),
]


def unreadable_record(brand: str, **changes: object) -> dict[str, object]:
    record: dict[str, object] = {
        "job_id": f"source-case-{brand.casefold().replace(' ', '-')}",
        "completed": True,
        "brand": brand,
        "installed_on": INSTALLED,
        "region": "TX",
        "model_reading": "DX4SQ" if brand.casefold() == "daikin" else "unreadable",
        "model_confirmation": "",
        "serial_reading": "unreadable",
        "serial_confirmation": "",
        "serial_format_validated": False,
        "homeowner_name": "Synthetic Homeowner",
        "homeowner_email": "homeowner@example.test",
    }
    record.update(changes)
    return record


@pytest.mark.parametrize("brand,family_id,days,deadline,source_url", SOURCE_CASES)
def test_brand_policy_deadline_is_separate_from_unit_eligibility(
    brand: str, family_id: str, days: int, deadline: str, source_url: str
) -> None:
    """An official window may be calculated, but cannot certify this unreadable unit."""
    result = evaluate_install(unreadable_record(brand), as_of=AS_OF)

    assert result["registration_deadline"] == deadline, source_url
    assert result["official_registration_guidance"]["family_id"] == family_id
    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "hold"
    assert result["portal_automation_allowed"] is False
    assert BRAND_RULES[brand.casefold()]["window_days"] == days
    # Policy wording itself stays conditional; no generic rule calls a unit eligible.
    assert "eligible" in result["official_registration_guidance"]["registration_deadline"].casefold()


@pytest.mark.parametrize(
    "brand,field_changes",
    [
        pytest.param("Carrier", {"model_reading": "", "serial_reading": "unreadable"}, id="missing-model"),
        pytest.param("Trane", {"model_reading": "XR-15", "serial_reading": ""}, id="missing-serial"),
        pytest.param("Goodman", {"model_reading": "??", "serial_reading": "?"}, id="unreadable-model-and-serial"),
    ],
)
def test_unreadable_or_missing_plate_data_never_becomes_registration_ready(
    brand: str, field_changes: dict[str, str]
) -> None:
    result = evaluate_install(unreadable_record(brand, **field_changes), as_of=AS_OF)

    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "hold"
    assert result["portal_automation_allowed"] is False
    assert result["result"] != "match"


def test_goodman_california_exception_is_not_a_coverage_eligibility_finding() -> None:
    """Goodman says CA residents need not register for registered-owner rights."""
    result = evaluate_install(
        unreadable_record("Goodman", region="CA"), as_of=AS_OF
    )

    assert result["registration_action"] == "skip"
    assert result["portal_automation_allowed"] is False
    # Skipping an unnecessary registration must not be reported as a unit match.
    assert result["result"] != "match"
    assert result["result"] == "no match found in registration-required regions as of 2026-02-01"
    assert result["official_registration_guidance"]["family_id"] == "goodman-amana"


def test_lennox_florida_keeps_the_published_60_day_change_window_visible() -> None:
    """Florida gets default coverage, with a 60-day window to change coverage choice."""
    result = evaluate_install(
        unreadable_record("Lennox", region="FL"), as_of=AS_OF
    )

    # Lennox's official page: Florida homeowners automatically receive the
    # default parts-only Extended Limited Warranty and may change to the
    # alternative parts-and-labor option within 60 days of installation.
    # The unit is still uncertain because its model and serial are unreadable.
    assert result["registration_deadline"] == "2026-03-02"
    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "hold"
    assert result["portal_automation_allowed"] is False
    assert "Florida" in BRAND_GUIDANCE["lennox"]["registration"]["deadline"] or "jurisdiction" in BRAND_GUIDANCE["lennox"]["registration"]["deadline"].casefold()


def test_rheem_without_a_universal_deadline_stays_uncertain_about_deadline_and_eligibility() -> None:
    """Rheem's official HVAC sources reviewed do not support one universal window."""
    result = evaluate_install(unreadable_record("Rheem"), as_of=AS_OF)

    assert result["registration_deadline"] is None
    assert result["result"] == "uncertain — please check"
    assert result["registration_action"] == "hold"
    assert result["portal_automation_allowed"] is False
    guidance = result["official_registration_guidance"]
    assert "uncertain" in guidance["registration_deadline"].casefold()
    assert guidance["family_id"] == "rheem-ruud"
