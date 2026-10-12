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


BRANDS_DIR = Path(__file__).resolve().parents[1] / "brands"


def load_brand_guidance() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load official brand guidance and map normalized names to family records."""
    families: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for path in sorted(BRANDS_DIR.glob("*.json")):
        family = json.loads(path.read_text(encoding="utf-8"))
        families[family["id"]] = family
        for name in family["brand_names"]:
            by_name[re.sub(r"[^a-z0-9]+", "", name.casefold())] = family
    return families, by_name


BRAND_GUIDANCE, BRAND_FAMILIES_BY_NAME = load_brand_guidance()
BRAND_RULES: dict[str, dict[str, Any]] = {
    normalized_name: {
        "window_days": family.get("queue_window_days"),
        "serial_pattern": None,
        "source": family["sources"][0]["url"],
    }
    for normalized_name, family in BRAND_FAMILIES_BY_NAME.items()
}


def _queue_brand_guidance(family: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep the queue reviewable while pointing to the full source-backed record."""
    if family is None:
        return None
    registration = family["registration"]
    date_code = family["date_code"]
    return {
        "family_id": family["id"],
        "source_record": f"ventures/warranty/brands/{family['id']}.json",
        "registration_deadline": registration["deadline"],
        "who_may_register": registration["who_may_register"],
        "portal_urls": registration["portal_urls"],
        "portal_accepts_dealer": "yes" if registration["portal_accepts_dealer"].startswith("yes") else "uncertain - please check",
        "terms_allow_third_party_preparation": (
            "uncertain - please check"
            if "uncertain" in registration["terms_allow_third_party_preparation"].casefold()
            else registration["terms_allow_third_party_preparation"]
        ),
        "date_code_status": date_code["status"],
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
    brand = re.sub(r"[^a-z0-9]+", "", str(record.get("brand", "")).strip().casefold())
    family = BRAND_FAMILIES_BY_NAME.get(brand)
    rules = rules_by_brand.get(brand)
    if rules is None:
        return _uncertain("brand is not in the reviewed brand list")
    if not record.get("completed"):
        return _uncertain("Jobber job is not confirmed complete", official_registration_guidance=_queue_brand_guidance(family))

    try:
        installed = date.fromisoformat(str(record["installed_on"]))
    except (KeyError, TypeError, ValueError):
        return _uncertain("installation date is missing or invalid", official_registration_guidance=_queue_brand_guidance(family))

    canonical_brand = family["primary_brand"] if family else brand
    region = str(record.get("region", "")).strip().upper()
    state_windows = family.get("registration", {}).get("state_windows", {}) if family else {}
    state_window = state_windows.get(region)
    if state_window and state_window.get("effective_on_or_after"):
        effective_on = date.fromisoformat(state_window["effective_on_or_after"])
        if installed < effective_on:
            state_window = None
    registration_exception = _is_registration_exception(canonical_brand, region, installed)
    if registration_exception and not state_window:
        return {
            "result": f"no match found in registration-required regions as of {as_of.isoformat()}",
            "reason": "spec-listed registration exception; confirm the applicable product warranty",
            "registration_action": "skip",
            "registration_deadline": None,
            "days_remaining": None,
            "deadline_alert": False,
            "portal_automation_allowed": False,
            "official_registration_guidance": _queue_brand_guidance(family),
            "photo_request_draft": None,
        }
    window_days = int(state_window["window_days"]) if state_window else rules.get("window_days")
    registration_source_url = (
        state_window.get("source_url") if state_window else rules.get("source")
    )

    result_fields: dict[str, Any] = {
        "official_registration_guidance": _queue_brand_guidance(family),
        "portal_automation_allowed": bool(PORTAL_AUTOMATION_ALLOWED.get(brand, False)),
        "registration_source_url": registration_source_url,
    }
    if state_window:
        result_fields["registration_window"] = {
            "label": state_window["label"],
            "window_type": state_window["window_type"],
            "description": state_window["description"],
            "source_url": registration_source_url,
        }
    if window_days is None:
        result_fields.update({"registration_deadline": None, "days_remaining": None, "deadline_alert": False})
    else:
        deadline = installed + timedelta(days=int(window_days))
        days_remaining = (deadline - as_of).days
        result_fields.update({
            "registration_deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
            "deadline_alert": 0 <= days_remaining <= 10 and not record.get("registered"),
        })

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
    serial_pattern = rules.get("serial_pattern")
    if not record.get("serial_format_validated") or not serial_pattern or not re.fullmatch(str(serial_pattern), serial):
        return _uncertain("brand serial format is not verified or did not match", **result_fields)
    if model != model_confirmation or serial != serial_confirmation:
        return _uncertain("independent model and serial readings do not agree", **result_fields)
    if not record.get("homeowner_name") or not _valid_email(record.get("homeowner_email")):
        return _uncertain("homeowner name or email is missing or invalid", **result_fields)
    if record.get("registered") and not record.get("confirmation_path"):
        return _uncertain("registered unit has no saved confirmation", **result_fields)
    if canonical_brand == "daikin":
        return _uncertain("Daikin terms do not permit automated portal handling", registration_action="owner_check_required", **result_fields)
    if registration_exception:
        return {
            "result": f"no match found in registration-required regions as of {as_of.isoformat()}",
            "reason": "spec-listed registration exception; confirm the applicable product warranty",
            "registration_action": "skip",
            **result_fields,
            "photo_request_draft": None,
        }

    return {
        "result": "match",
        "reason": "confirmed intake matches the source-backed local checks; registration is still held for owner review",
        "registration_action": "skip" if record.get("registered") else "owner_check_required",
        **result_fields,
        "photo_request_draft": None,
    }


def _jobber_custom_field_map(job: dict[str, Any]) -> dict[str, str]:
    """Map Jobber text custom fields by their account-configured labels."""
    fields: dict[str, str] = {}
    for item in job.get("customFields") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("name") or "").strip().casefold()
        value = item.get("valueText")
        if label and value is not None:
            fields[re.sub(r"[^a-z0-9]+", "", label)] = str(value).strip()
    return fields


def _jobber_unit(job: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one completed Jobber job response into the local intake shape."""
    status = str(job.get("jobStatus") or "").strip().upper()
    completed_at = job.get("completedAt")
    if not completed_at and status not in {"COMPLETED", "COMPLETE"}:
        return None
    fields = _jobber_custom_field_map(job)
    client = job.get("client") if isinstance(job.get("client"), dict) else {}
    property_data = job.get("property") if isinstance(job.get("property"), dict) else {}
    address = property_data.get("address") if isinstance(property_data.get("address"), dict) else {}

    def value(*labels: str) -> str:
        return next((fields[key] for label in labels if (key := re.sub(r"[^a-z0-9]+", "", label.casefold())) in fields), "")

    installed_on = value("Install Date", "Installation Date", "Installed On")
    brand = value("Equipment Brand", "Brand", "Manufacturer")
    model = value("Equipment Model", "Model")
    serial = value("Equipment Serial", "Serial", "Serial Number")
    region = value("Region", "State", "Province") or str(address.get("province") or address.get("state") or "")
    homeowner_name = str(client.get("name") or "").strip()
    homeowner_email = str(client.get("email") or "").strip()
    return {
        "job_id": str(job.get("id") or ""),
        "job_number": job.get("jobNumber"),
        "job_title": str(job.get("title") or ""),
        "completed": bool(completed_at) or status in {"COMPLETED", "COMPLETE"},
        "brand": brand,
        "model_reading": model,
        "model_confirmation": "",
        "serial_reading": serial,
        "serial_confirmation": "",
        "serial_format_validated": False,
        "installed_on": installed_on,
        "region": region,
        "homeowner_name": homeowner_name,
        "homeowner_email": homeowner_email,
        "technician_opted_in": False,
        "intake_source": "Jobber read-only",
    }


def build_jobber_loop(jobs: list[dict[str, Any]], *, as_of: date | None = None) -> dict[str, Any]:
    """Build deadline queue and unsent homeowner drafts from Jobber GraphQL jobs."""
    units = [unit for job in jobs if isinstance(job, dict) if (unit := _jobber_unit(job)) is not None]
    batch = prepare_batch(units, as_of=as_of)
    queue: list[dict[str, Any]] = []
    drafts: list[dict[str, Any]] = []
    for item in batch["units"]:
        unit = item["unit"]
        assessment = {key: value for key, value in item.items() if key != "unit"}
        queue.append({**unit, **assessment})
        if _valid_email(unit.get("homeowner_email")):
            deadline = assessment.get("registration_deadline")
            deadline_text = date.fromisoformat(deadline).strftime("%B %d, %Y").replace(" 0", " ") if deadline else "not yet available"
            window = assessment.get("registration_window") or {}
            if window.get("window_type") == "coverage-change window":
                deadline_label = "The published deadline to change coverage choice is"
                status_text = "This draft does not change the manufacturer's published default coverage."
            else:
                deadline_label = "The registration deadline is"
                status_text = "The equipment is not registered yet. We will follow up after review."
            source_url = assessment.get("registration_source_url")
            policy_text = (
                f"\n\n{window['label']} warranty guidance: {window['description']} "
                f"Source: {window['source_url']}"
                if window else (f"\n\nOfficial warranty source: {source_url}" if source_url else "")
            )
            drafts.append({
                "job_id": unit["job_id"],
                "to": unit["homeowner_email"],
                "subject": "Warranty registration follow-up for your HVAC installation",
                "body": (
                    f"Hello {unit['homeowner_name'] or 'there'},\n\n"
                    f"We are preparing the warranty registration details for your {unit.get('brand') or 'HVAC'} "
                    f"installation on {unit.get('installed_on') or 'the recorded installation date'}. "
                    f"{deadline_label} {deadline_text}. The equipment details are still being checked. "
                    f"{status_text}{policy_text}\n\n"
                    "Your service team"
                ),
                "sent": False,
                "requires_owner_review": True,
            })
    return {
        "source": "Jobber read-only GraphQL API",
        "as_of": (as_of or date.today()).isoformat(),
        "registration_queue": queue,
        "homeowner_email_drafts": drafts,
        "duplicates": batch["duplicates"],
        "units": units,
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
    own_client = client is None
    connector = client or JobberClient()
    try:
        return connector.get_jobs(max_pages=5)
    finally:
        if own_client:
            connector.close()


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
    parser.add_argument("--fixture-jobs", type=Path, help="local Jobber GraphQL fixture; never makes a network request")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    try:
        if args.action == "jobber-preview":
            if args.fixture_jobs:
                fixture = json.loads(args.fixture_jobs.read_text(encoding="utf-8"))
                jobs = JobberClient._normalize_jobs(fixture)
            else:
                jobs = read_jobber_jobs()
            output: Any = build_jobber_loop(jobs, as_of=args.as_of)
            home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
            target = home / "ventures" / "warranty" / "pending-units.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"units": output["units"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            output["result"] = "match" if output["registration_queue"] else f"no match found in Jobber as of {args.as_of.isoformat()}"
            output["local_queue_file"] = str(target)
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
