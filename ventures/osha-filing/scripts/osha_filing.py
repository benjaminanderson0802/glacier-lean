"""Prepare OSHA Form 300A packets and approved, render-only outreach drafts.

This venture never certifies or submits an OSHA filing. A customer reviews,
signs, enters, and submits the prepared data in the OSHA ITA.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ventures.blocks import feeds
from ventures.blocks.connectors import JobberClient
from ventures.blocks.deadlines import add as add_deadline, due as due_deadlines
from ventures.blocks.filer import prepare as filer_prepare
from ventures.blocks.mail import landing_pages, postcard
from ventures.blocks.rules import check

OSHA_FORM = "https://www.osha.gov/recordkeeping/forms"
OSHA_INDUSTRIES = "https://www.osha.gov/recordkeeping/naics-codes-electronic-submission"
ITA = "https://www.osha.gov/injuryreporting/"
SOURCE_ID = "osha_ita"
HIGH_HAZARD_NAICS_PREFIXES = (
    "11", "22", "23", "31", "32", "33", "42", "4413", "4421", "4422", "4441", "4442",
    "4451", "4452", "4521", "4529", "4533", "4542", "4543", "4811", "4841", "4842",
    "4851", "4852", "4853", "4854", "4855", "4859", "4871", "4881", "4882", "4883",
    "4884", "4889", "4911", "4921", "4922", "4931", "5152", "5311", "5321", "5322",
    "5323", "5617", "5621", "5622", "5629", "6219", "6221", "6222", "6223", "6231",
    "6232", "6233", "6239", "6242", "6243", "7111", "7112", "7121", "7131", "7132",
    "7211", "7212", "7213", "7223", "8113", "8123",
)

# These are field-shape checks only. Relational checks below are deterministic
# preparation checks, not a determination of legal coverage or compliance.
FORM_RULESET: dict[str, Any] = {
    "id": "osha_form_300a_preparation",
    "title": "OSHA Form 300A preparation fields",
    "source": {"title": "OSHA Form 300A and instructions", "url": OSHA_FORM},
    "rules": [
        {"id": "osha.establishment_name", "field": "establishment_name", "check": "non_empty", "section": "Form 300A establishment information"},
        {"id": "osha.year", "field": "year", "check": "non_empty", "section": "Form 300A year"},
        {"id": "osha.average_employees", "field": "average_employees", "check": "non_empty", "section": "Form 300A average number of employees"},
        {"id": "osha.total_hours_worked", "field": "total_hours_worked", "check": "non_empty", "section": "Form 300A total hours worked"},
        {"id": "osha.executive_name", "field": "executive_name", "check": "non_empty", "section": "Form 300A executive certification"},
    ],
}

COUNT_FIELDS = (
    "total_deaths",
    "cases_with_days_away",
    "cases_with_job_transfer_or_restriction",
    "other_recordable_cases",
    "total_cases",
    "days_away",
    "job_transfer_or_restriction_days",
)


def _int_field(fields: dict[str, Any], name: str) -> int | None:
    value = fields.get(name)
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if str(value).strip() == str(number) and number >= 0 else None


def validate_300a(fields: dict[str, Any]) -> dict[str, Any]:
    """Use the shared cited field checker plus OSHA Form 300A arithmetic checks."""
    result = check(fields, FORM_RULESET)
    checks: list[dict[str, Any]] = []
    year = _int_field(fields, "year")
    checks.append({"rule": "osha.year_format", "verdict": "pass" if year and 2000 <= year <= 2099 else "fail" if fields.get("year") not in (None, "") else "uncertain", "cite": OSHA_FORM, "detail": "Enter a four-digit calendar year for the summary."})
    counts = {name: _int_field(fields, name) for name in COUNT_FIELDS}
    absent = [name for name, value in counts.items() if value is None]
    if absent:
        checks.append({"rule": "osha.case_totals_present", "verdict": "uncertain", "cite": OSHA_FORM, "detail": "Customer must confirm nonnegative whole-number case and day totals for: " + ", ".join(absent)})
    else:
        expected = counts["total_deaths"] + counts["cases_with_days_away"] + counts["cases_with_job_transfer_or_restriction"] + counts["other_recordable_cases"]
        checks.append({"rule": "osha.total_cases_sum", "verdict": "pass" if counts["total_cases"] == expected else "fail", "cite": OSHA_FORM, "detail": "Total cases must equal the sum of the four Form 300A case categories."})
    average = _int_field(fields, "average_employees")
    hours = _int_field(fields, "total_hours_worked")
    if average is None or hours is None:
        checks.append({"rule": "osha.hours_plausibility", "verdict": "uncertain", "cite": OSHA_FORM, "detail": "Customer must confirm average employees and total hours as nonnegative whole numbers."})
    else:
        plausible = (average == 0 and hours == 0) or (average > 0 and 0 < hours <= average * 8760)
        checks.append({"rule": "osha.hours_plausibility", "verdict": "pass" if plausible else "fail", "cite": OSHA_FORM, "detail": "Hours must be positive for a staffed establishment and cannot exceed 8,760 hours per average employee."})
    result["results"].extend(checks)
    verdicts = {item["verdict"] for item in result["results"]}
    result["verdict"] = "fail" if "fail" in verdicts else "uncertain" if "uncertain" in verdicts else "pass"
    result["legal_conclusion"] = False
    return result


def build_300a_packet(fields: dict[str, Any]) -> dict[str, Any]:
    """Build a printable review draft with an intentionally blank certification."""
    validation = validate_300a(fields)
    escaped = {key: html.escape(str(value)) for key, value in fields.items()}
    labels = (
        ("establishment_name", "Establishment name"), ("establishment_address", "Street address"),
        ("establishment_city", "City"), ("establishment_state", "State"),
        ("establishment_zip", "ZIP code"), ("establishment_id", "OSHA establishment ID"),
        ("industry_code", "Industry code"), ("year", "Calendar year"),
        ("average_employees", "Average number of employees"), ("total_hours_worked", "Total hours worked"),
        ("total_deaths", "Deaths"), ("cases_with_days_away", "Cases with days away"),
        ("cases_with_job_transfer_or_restriction", "Cases with job transfer or restriction"),
        ("other_recordable_cases", "Other recordable cases"), ("total_cases", "Total cases"),
        ("days_away", "Days away from work"),
        ("job_transfer_or_restriction_days", "Job transfer or restriction days"),
        ("executive_name", "Executive name"), ("executive_title", "Executive title"),
    )
    rows = "".join(f"<tr><th>{label}</th><td>{escaped.get(key, 'Customer confirmation needed')}</td></tr>" for key, label in labels)
    html_doc = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>Form 300A preparation draft</title>"
        "<style>body{font:16px Arial,sans-serif;max-width:900px;margin:2rem auto;color:#222}table{width:100%;border-collapse:collapse}th,td{border:1px solid #777;padding:.5rem;text-align:left}th{width:40%}.notice{border:2px solid #8a2f00;padding:1rem}</style>"
        "<h1>OSHA Form 300A preparation draft</h1><p>Customer review copy. Compare every value with the establishment's OSHA 300 Log.</p>"
        f"<table>{rows}</table><h2>Executive certification</h2><p>{html.escape(str(fields.get('executive_name', 'Customer confirmation needed')))}, {html.escape(str(fields.get('executive_title', '')))}</p>"
        "<p>Signature: ____________________________________ &nbsp; Date: ______________</p>"
        f"<div class='notice'><strong>Customer action:</strong> executive signs and dates this form, posts it at the establishment February 1–April 30, and submits the required data in OSHA ITA during the Jan 2–Mar 2 window. Glacier does not certify or submit. Check current OSHA requirements at <a href='{ITA}'>OSHA ITA</a>.</div>"
        "</html>"
    )
    customer_result = "match" if validation["verdict"] == "pass" else "uncertain — please check"
    return {"html": html_doc, "result": customer_result, "validation": validation, "signature": "customer_signature_required", "submission": "customer_submits_in_osha_ita", "official_form": OSHA_FORM, "ita": ITA}


def prepare_ita_local_mock(fields: dict[str, Any], auth: dict[str, Any], *, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    """Use the shared filer only with a local OSHA-like test mock; no submission."""
    import re

    base_url = str(auth.get("base_url", ""))
    if not re.match(r"^http://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:/|$)", base_url):
        raise ValueError("OSHA filer preparation is disabled except for the local mock; customer completes and submits in OSHA ITA")
    return filer_prepare("osha-ita-local-mock", fields, auth, evidence_dir=evidence_dir)


def _row_data(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data")
    return data if isinstance(data, dict) else row


def _value(record: dict[str, Any], *names: str) -> Any:
    lowered = {str(key).casefold().replace(" ", "_"): value for key, value in record.items()}
    for name in names:
        value = lowered.get(name.casefold().replace(" ", "_"))
        if value not in (None, ""):
            return value
    return None


def refresh_public_data() -> dict[str, Any]:
    """Refresh the OSHA public submission index from the shared official feed."""
    return feeds.sync(SOURCE_ID)


def eligible_prospects(*, as_of: date | None = None, high_hazard_codes: set[str] | None = None) -> dict[str, Any]:
    """Return repeat-filer leads; uncertain industry cases remain excluded."""
    as_of = as_of or date.today()
    today_window = (as_of.month, as_of.day)
    if today_window > (3, 2):
        return {"result": "no match found in OSHA public submission data as of " + as_of.isoformat(), "prospects": [], "excluded": [], "sales": "waitlist_for_next_january"}
    rows = feeds.query(SOURCE_ID)
    prospects: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen: set[str] = set()
    allowed_codes = high_hazard_codes
    for row in rows:
        record = _row_data(row)
        establishment_id = str(_value(record, "establishment_id", "establishment id", "EstablishmentId") or row.get("record_id", "")).strip()
        if not establishment_id or establishment_id in seen:
            continue
        seen.add(establishment_id)
        count = _int_field({"n": _value(record, "employee_count", "employees", "average_employees", "number_of_employees", "annual_average_employees", "annual_average_number_of_employees", "annual_avg_employees", "average_number_of_employees")}, "n")
        industry = str(_value(record, "industry_code", "naics", "naics_code", "industry code", "primary_naics", "primary_naics_code") or "").strip()
        if count is not None and count >= 250:
            prospects.append({**record, "establishment_id": establishment_id, "prospect_result": "match", "source": row.get("source_url", OSHA_FORM), "as_of": as_of.isoformat()})
        elif count is not None and count >= 20 and ((industry in allowed_codes) if allowed_codes is not None else industry.startswith(HIGH_HAZARD_NAICS_PREFIXES)):
            prospects.append({**record, "establishment_id": establishment_id, "prospect_result": "match", "source": OSHA_INDUSTRIES, "as_of": as_of.isoformat()})
        else:
            excluded.append({"establishment_id": establishment_id, "result": "uncertain — please check", "reason": "employee count or designated high-hazard industry is not established from the available record", "industry_code": industry, "employee_count": count})
    return {"result": "match" if prospects else "no match found in OSHA public submission data as of " + as_of.isoformat(), "prospects": prospects, "excluded": excluded, "sales": "open"}


def render_outreach_proof(prospect: dict[str, Any], *, output_dir: str | Path) -> dict[str, Any]:
    """Render one postcard proof and distinct prefilled page; never mail it."""
    record = {**prospect, "id": str(prospect.get("establishment_id", "")), "sender": "Glacier Filing Preparation", "year": date.today().year - 1}
    front = "<h1>Glacier Filing Preparation</h1><p>Work injury summary preparation</p><p>For {{establishment_name}}</p><p>Private service offer from an independent business.</p>"
    back = "<p>Prepare your Form 300A with customer review. You complete, certify, and submit your filing.</p><p>Learn more: {{landing_url}}</p><p>Glacier Filing Preparation</p>"
    recipient = {"address_line1": _value(prospect, "address", "address_line1", "street_address") or "", "address_city": _value(prospect, "city") or "", "address_state": _value(prospect, "state") or "", "address_zip": _value(prospect, "zip", "zip_code", "postal_code") or ""}
    postcard_result = postcard(front, back, recipient, {"name": record["sender"], "address_line1": "", "address_city": "", "address_state": "", "address_zip": ""}, output_dir=output_dir)
    pages = landing_pages([record], "<!doctype html><meta charset='utf-8'><title>OSHA preparation</title><h1>Glacier OSHA filing preparation</h1><p>Establishment: {{establishment_name}}</p><p>OSHA establishment ID: {{establishment_id}}</p><p>Industry: {{industry_code}}</p><p>Customer certifies and submits through OSHA ITA; Glacier never acts as OSHA.</p>", output_dir=Path(output_dir) / "landing")
    return {"postcard": postcard_result, "landing_pages": pages, "mail_status": "render_only", "approval_required_before_any_live_mailing": True}


def schedule_deadlines(item_id: str, year: int, label: str) -> None:
    add_deadline(item_id, f"{year}-01-02", "jan2-mar2", label)
    add_deadline(item_id + "-posting", f"{year}-02-01", f"{year}-02-01|{year}-04-30", label + " workplace posting period")


def jobber_preview(client: JobberClient | None = None) -> dict[str, Any]:
    """Read Jobber via the shared connector; do not infer staff count from job titles."""
    jobs = (client or JobberClient()).get_jobs(max_pages=5)
    candidates = [job for job in jobs if _int_field({"n": job.get("employee_count")}, "n") is not None and int(job["employee_count"]) >= 20]
    unverified = len([job for job in jobs if job.get("employee_count") in (None, "")])
    result = "uncertain — please check" if unverified else "match" if candidates else "no match found in Jobber as of " + date.today().isoformat()
    return {"result": result, "jobs_reviewed": len(jobs), "candidate_jobs": candidates, "unverified_jobs_missing_staff_count": unverified, "read_only": True, "detail": "Jobber's shared read-only connector currently exposes job IDs, numbers, and titles only; it cannot determine shop staff count or support marketplace listing publication."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("sync")
    leads = sub.add_parser("prospects")
    leads.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    leads.add_argument("--output", type=Path, help="local path for a single address-complete candidate; never writes the full public dataset")
    prepare = sub.add_parser("prepare-300a")
    prepare.add_argument("--input", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    sub.add_parser("jobber-preview")
    preview = sub.add_parser("postcard-preview")
    preview.add_argument("--input", type=Path, required=True)
    preview.add_argument("--output", type=Path, default=Path("data/ventures/osha-filing/outreach"))
    reminders = sub.add_parser("deadlines")
    reminders.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args(argv)
    try:
        if args.action == "sync":
            output: Any = refresh_public_data()
        elif args.action == "prospects":
            result = eligible_prospects(as_of=args.as_of)
            selected = next((row for row in result["prospects"] if all(_value(row, *names) for names in (("street_address", "address", "address_line1"), ("city",), ("state",), ("zip_code", "zip", "postal_code")))), None)
            target = args.output or Path(__import__("os").environ.get("GLACIER_HOME", str(Path.home() / ".glacier"))) / "ventures" / "osha-filing" / "selected-prospect.json"
            selected_path = None
            if selected is not None:
                # Persist only the fields needed to render the review proof; the
                # source feed can contain EINs and unrelated fields.
                slim = {
                    "establishment_id": _value(selected, "establishment_id", "establishment id"),
                    "establishment_name": _value(selected, "establishment_name", "company_name", "company name"),
                    "industry_code": _value(selected, "industry_code", "naics_code", "naics"),
                    "employee_count": _value(selected, "annual_average_employees", "employee_count"),
                    "address": _value(selected, "street_address", "address", "address_line1"),
                    "city": _value(selected, "city"),
                    "state": _value(selected, "state"),
                    "zip_code": _value(selected, "zip_code", "zip", "postal_code"),
                    "source": selected.get("source", OSHA_FORM),
                    "as_of": args.as_of.isoformat(),
                    "result": "match",
                }
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
                selected_path = str(target)
            status_path = target.parent / "prospect-status.json"
            public_result = result["result"] if selected or not result["prospects"] else "uncertain — please check"
            status_path.write_text(json.dumps({"result": public_result, "as_of": args.as_of.isoformat(), "candidate_count": len(result["prospects"]), "uncertain_count": len(result["excluded"]), "selected_prospect_path": selected_path, "sales": result.get("sales", "open")}, indent=2, ensure_ascii=False), encoding="utf-8")
            output = {"result": public_result, "candidate_count": len(result["prospects"]), "uncertain_count": len(result["excluded"]), "selected_prospect_path": selected_path, "detail": "Only a single minimum-field candidate is saved for postcard proof review; no complete mailing list is exported."}
        elif args.action == "prepare-300a":
            fields = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(fields, dict):
                raise ValueError("input must be one JSON object with customer-confirmed fields")
            packet = build_300a_packet(fields)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(packet["html"], encoding="utf-8")
            if fields.get("establishment_id") and _int_field(fields, "year"):
                schedule_deadlines(str(fields["establishment_id"]), int(fields["year"]) + 1, "OSHA Form 300A filing window")
            output = {"output": str(args.output), "result": packet["result"], "check_details": packet["validation"]["results"], "signature": packet["signature"], "submission": packet["submission"]}
        elif args.action == "postcard-preview":
            if not args.input.is_file():
                output = {"result": "no match found in OSHA public submission data as of " + date.today().isoformat(), "mail_status": "not_sent", "detail": "There is no address-complete, reviewed prospect for postcard proof generation."}
                print(json.dumps(output, indent=2, sort_keys=True, default=str))
                return 0
            prospect = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(prospect, dict):
                raise ValueError("selected prospect must be a JSON object")
            output = render_outreach_proof(prospect, output_dir=args.output)
        elif args.action == "deadlines":
            due = due_deadlines(args.as_of)
            output = {"due": due, "customer_submits": True, "certification_by_glacier": False}
            home = Path(__import__("os").environ.get("GLACIER_HOME", str(Path.home() / ".glacier")))
            status_path = home / "ventures" / "osha-filing" / "deadline-status.json"
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_text(json.dumps({"as_of": args.as_of.isoformat(), "due_count": len(due), "customer_submits": True, "certification_by_glacier": False}, indent=2), encoding="utf-8")
        else:
            output = jobber_preview()
        print(json.dumps(output, indent=2, sort_keys=True, default=str))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "uncertain — please check", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
