"""Conservative HVAC warranty intake and deadline preparation.

This module never sends email or submits a brand portal form. Brand rules with
no verified serial format stay uncertain, and no brand currently permits
automated portal work in the checked-in configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ventures.blocks.connectors import JobberClient
from ventures.blocks.filer import prepare as filer_prepare


BRAND_RULES: dict[str, dict[str, Any]] = {
    "trane": {"window_days": 60, "serial_pattern": None, "source": "https://www.trane.com/residential/en/resources/warranty-and-registration/"},
    "goodman": {"window_days": 60, "serial_pattern": None, "source": "https://warranty.goodmanmfg.com/newregistration/"},
    "daikin": {"window_days": 60, "serial_pattern": None, "source": "https://daikincomfort.com/terms-of-use"},
    "lennox": {"window_days": 60, "serial_pattern": None, "source": "https://www.lennox.com/residential/owners/register-and-review/product-registration/index"},
    "carrier": {"window_days": 90, "serial_pattern": None, "source": "https://www.carrier.com/us/en/residential/homeowner-resources/warranty/"},
}

# A positive result requires an owner-maintained, source-backed serial regex.
# None means terms and format have not been verified for automated handling.
PORTAL_AUTOMATION_ALLOWED = {brand: False for brand in BRAND_RULES}


def prepare_local_mock(fields: dict[str, Any], auth: dict[str, Any], *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    """Exercise the shared filer only against its local acceptance mock."""
    base_url = str(auth.get("base_url", ""))
    if not re.match(r"^http://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:/|$)", base_url):
        raise ValueError("warranty portal preparation is disabled except for the local mock")
    return filer_prepare("warranty-local-mock", fields, auth, evidence_dir=evidence_dir)


def _uncertain(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "result": "uncertain — please check",
        "reason": reason,
        "registration_action": "hold",
        "deadline_alert": False,
        "portal_automation_allowed": False,
        "photo_request_draft": None,
        **extra,
    }


def _valid_email(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is not None


def _is_registration_exception(brand: str, region: str, installed: date) -> bool:
    if region in {"CA", "QC"}:
        return True
    return brand == "lennox" and region in {"FL", "GA"} and installed >= date(2026, 1, 1)


def evaluate_install(
    record: dict[str, Any],
    *,
    as_of: date | None = None,
    brand_rules: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate one install and calculate its reminder date without side effects."""
    as_of = as_of or date.today()
    rules_by_brand = brand_rules if brand_rules is not None else BRAND_RULES
    brand = str(record.get("brand", "")).strip().lower()
    rules = rules_by_brand.get(brand)
    if rules is None:
        return _uncertain("brand is not in the reviewed brand list")
    if not record.get("completed"):
        return _uncertain("Jobber job is not confirmed complete")

    try:
        installed = date.fromisoformat(str(record["installed_on"]))
    except (KeyError, TypeError, ValueError):
        return _uncertain("installation date is missing or invalid")

    if _is_registration_exception(brand, str(record.get("region", "")).strip().upper(), installed):
        return {
            "result": f"no match found in registration-required regions as of {as_of.isoformat()}",
            "reason": "spec-listed registration exception; confirm the applicable product warranty",
            "registration_action": "skip",
            "registration_deadline": None,
            "days_remaining": None,
            "deadline_alert": False,
            "portal_automation_allowed": False,
            "photo_request_draft": None,
        }

    deadline = installed + timedelta(days=int(rules["window_days"]))
    days_remaining = (deadline - as_of).days
    result_fields: dict[str, Any] = {
        "registration_deadline": deadline.isoformat(),
        "days_remaining": days_remaining,
        "deadline_alert": 0 <= days_remaining <= 10 and not record.get("registered"),
        "portal_automation_allowed": bool(PORTAL_AUTOMATION_ALLOWED.get(brand, False)),
    }

    model = str(record.get("model_reading", "")).strip()
    serial = str(record.get("serial_reading", "")).strip().upper()
    model_confirmation = str(record.get("model_confirmation", "")).strip()
    serial_confirmation = str(record.get("serial_confirmation", "")).strip().upper()
    missing_plate_data = not model or not serial
    photo_request_draft = None
    if missing_plate_data and record.get("technician_opted_in"):
        photo_request_draft = {
            "to": str(record.get("technician_contact", "")),
            "text": "Please retake the HVAC data-plate photo so we can read the model and serial number.",
            "sent": False,
        }

    if missing_plate_data:
        return _uncertain("data-plate model or serial is missing", **result_fields, photo_request_draft=photo_request_draft)
    if model != model_confirmation or serial != serial_confirmation:
        return _uncertain("independent model and serial readings do not agree", **result_fields)
    serial_pattern = rules.get("serial_pattern")
    if not record.get("serial_format_validated") or not serial_pattern or not re.fullmatch(str(serial_pattern), serial):
        return _uncertain("brand serial format is not verified or did not match", **result_fields)
    if not record.get("homeowner_name") or not _valid_email(record.get("homeowner_email")):
        return _uncertain("homeowner name or email is missing or invalid", **result_fields)
    if record.get("registered") and not record.get("confirmation_path"):
        return _uncertain("registered unit has no saved confirmation", **result_fields)
    if brand == "daikin":
        return _uncertain("Daikin terms do not permit automated portal handling", registration_action="owner_check_required", **result_fields)

    return {
        "result": "match",
        "reason": "confirmed intake matches the source-backed local checks; registration is still held for owner review",
        "registration_action": "skip" if record.get("registered") else "owner_check_required",
        **result_fields,
        "photo_request_draft": None,
    }


def prepare_batch(
    units: list[dict[str, Any]], *, as_of: date | None = None,
    brand_rules: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return one item per unit key, recording duplicate keys without preparing twice."""
    seen: set[str] = set()
    duplicates: list[str] = []
    results: list[dict[str, Any]] = []
    for unit in units:
        key = str(unit.get("unit_id") or unit.get("serial_reading") or unit.get("job_id") or "").strip()
        if not key:
            results.append({"unit": unit, **_uncertain("unit has no stable identifier")})
            continue
        if key in seen:
            duplicates.append(key)
            continue
        seen.add(key)
        results.append({"unit": unit, **evaluate_install(unit, as_of=as_of, brand_rules=brand_rules)})
    return {"units": results, "duplicates": duplicates}


def read_jobber_jobs(client: JobberClient | None = None) -> list[dict[str, Any]]:
    """Read Jobber jobs through the shared read-only connector."""
    return (client or JobberClient()).get_jobs(max_pages=5)


def _load_units(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    units = data.get("units", data) if isinstance(data, dict) else data
    if not isinstance(units, list) or any(not isinstance(unit, dict) for unit in units):
        raise ValueError("input must be a JSON list of unit records or an object with a units list")
    return units


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("evaluate", "deadlines", "jobber-preview"))
    parser.add_argument("--input", type=Path, help="JSON file containing normalized install records")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    try:
        if args.action == "jobber-preview":
            jobs = read_jobber_jobs()
            output: Any = {
                "result": "match" if jobs else f"no match found in Jobber as of {args.as_of.isoformat()}",
                "source": "Jobber read-only connector",
                "jobs": jobs,
            }
        else:
            if args.input is None and args.action == "evaluate":
                raise ValueError("--input is required for evaluate")
            home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
            input_path = args.input or home / "ventures" / "warranty" / "pending-units.json"
            if not input_path.is_file() and args.action == "deadlines":
                output = {"result": "no match found in local warranty intake as of " + args.as_of.isoformat(), "units": [], "alerts": []}
            else:
                batch = prepare_batch(_load_units(input_path), as_of=args.as_of)
                if args.action == "deadlines":
                    due = [unit for unit in batch["units"] if unit.get("deadline_alert")]
                    output = {"result": "match" if due else "no match found in local warranty intake as of " + args.as_of.isoformat(), "units": batch["units"], "alerts": due}
                else:
                    output = batch
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"result": "uncertain — please check", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
