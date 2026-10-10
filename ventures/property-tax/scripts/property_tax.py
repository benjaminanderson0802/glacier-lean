"""Prepare customer-reviewed Cook County property-tax appeal packets and mail proofs."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ventures.blocks import customer, deadlines, mail, reader
from ventures.blocks.feeds import query, sync


COUNTY = "Cook County"
COUNTY_SOURCE = "cook_county_assessor"
COUNTY_SOURCE_URL = "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.json"
NOTICE_SCHEMA = {
    "parcel_id": ["PIN", "Parcel Identification Number"],
    "assessed_value": ["Assessed Value", "Total Assessed Value"],
}
COMPARABLE_SCHEMA = {
    "sale_date": ["Sale Date", "Date of Sale"],
    "sale_price": ["Sale Price", "Transfer Price"],
    "square_feet": ["Square Feet", "Building Area"],
}


def _field_value(fields: dict[str, Any], key: str) -> Any:
    entry = fields.get(key) or {}
    value = entry.get("value")
    if value in (None, "") or entry.get("uncertain") is True or float(entry.get("confidence", 0)) < 0.8:
        return None
    return value


def _number(value: Any) -> float | None:
    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        number = float(cleaned)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _normalize_pin(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(14) if digits and len(digits) <= 14 else digits


def find_roll_parcel(parcel_id: str, feed_rows: list[dict[str, Any]], *, on_date: date | None = None) -> dict[str, Any]:
    """Find a parcel in the shared public-feed snapshot without inferring ownership."""
    wanted = _normalize_pin(parcel_id)
    match = next((row for row in feed_rows if _normalize_pin(row.get("record_id")) == wanted), None)
    day = on_date or date.today()
    if match is None:
        return {"result": f"no match found in Cook County Assessor parcel roll as of {day.isoformat()}", "parcel": None}
    data = match.get("data", {})
    return {
        "result": "match",
        "parcel": {
            "parcel_id": str(match["record_id"]),
            "class": data.get("class"),
            "township": data.get("township_name"),
            "zip_code": data.get("zip_code"),
            "tax_year": data.get("year"),
            "source_url": match.get("source_url") or COUNTY_SOURCE_URL,
            "fetched_at": match.get("fetched_at"),
        },
    }


def build_packet(case: dict[str, Any], feed_rows: list[dict[str, Any]], *, today: date | None = None) -> dict[str, Any]:
    """Read notice and sale evidence; uncertain or incomplete data stays with the customer."""
    as_of = today or date.today()
    parcel_result = find_roll_parcel(case.get("parcel_id", ""), feed_rows, on_date=as_of)
    base: dict[str, Any] = {
        "venture": "property-tax",
        "county": case.get("county", COUNTY),
        "parcel_id": str(case.get("parcel_id", "")),
        "result": parcel_result["result"],
        "status": "no_roll_match" if parcel_result["parcel"] is None else "needs_customer_confirmation",
        "as_of": as_of.isoformat(),
        "filing_submitted": False,
        "legal_review_notice": "The customer decides whether the records support an appeal, confirms the requested value, signs, and submits the filing. This packet is not legal advice or a filing.",
        "parcel": parcel_result["parcel"],
        "comparables": [],
        "customer_requested_value": case.get("customer_requested_value"),
        "uncertainties": [],
    }
    if parcel_result["parcel"] is None:
        base["uncertainties"].append("Parcel was not found in the local Cook County feed snapshot; refresh the source and check the PIN.")
        return base

    notice_path = case.get("notice_path")
    if not notice_path or not Path(notice_path).is_file():
        base["uncertainties"].append("Customer's current assessment notice is missing.")
    else:
        notice = reader.read_document(notice_path, NOTICE_SCHEMA)
        notice_pin = _field_value(notice.get("fields", {}), "parcel_id")
        assessed_value = _number(_field_value(notice.get("fields", {}), "assessed_value"))
        if notice_pin and _normalize_pin(notice_pin) != _normalize_pin(base["parcel_id"]):
            base["uncertainties"].append("Notice PIN does not match the requested parcel.")
        if assessed_value is None:
            base["uncertainties"].append("Notice assessed value is missing or uncertain.")
        else:
            base["assessment_notice"] = {"assessed_value": assessed_value, "source_path": str(notice_path), "source_url": case.get("notice_source_url"), "as_of": case.get("notice_date")}

    notice_day = _day(case.get("notice_date"))
    deadline = _day(case.get("deadline"))
    if notice_day is None or deadline is None or deadline <= (notice_day or as_of):
        base["uncertainties"].append("A valid notice date and later county deadline are required.")
    elif deadline < as_of:
        base["uncertainties"].append("The supplied appeal deadline has passed; confirm the current county deadline.")

    subject_sqft = _number(case.get("subject_square_feet"))
    comp_rows = case.get("comparables", [])
    comp_dates: list[date] = []
    unit_values: list[float] = []
    for comp in comp_rows:
        path = comp.get("path")
        if not path or not Path(path).is_file():
            base["uncertainties"].append("A comparable-sales document is missing.")
            continue
        extracted = reader.read_document(path, COMPARABLE_SCHEMA)
        fields = extracted.get("fields", {})
        sale_date = _day(_field_value(fields, "sale_date"))
        price = _number(_field_value(fields, "sale_price"))
        sqft = _number(_field_value(fields, "square_feet"))
        if not sale_date or not price or not sqft:
            base["uncertainties"].append(f"Comparable at {comp.get('source_url', path)} has missing or uncertain sale date, price, or area.")
            continue
        age_limit = notice_day or as_of
        if sale_date > age_limit or sale_date < age_limit - timedelta(days=365):
            base["uncertainties"].append(f"Comparable at {comp.get('source_url', path)} is outside the 12 months before the notice date.")
            continue
        if not comp.get("arms_length_confirmed"):
            base["uncertainties"].append(f"Customer must confirm this sale was arm's-length: {comp.get('source_url', path)}.")
            continue
        evidence = {
            "sale_date": fields["sale_date"],
            "sale_price": fields["sale_price"],
            "square_feet": fields["square_feet"],
            "source_url": comp.get("source_url"),
            "arms_length_confirmed_by_customer": True,
        }
        base["comparables"].append(evidence)
        comp_dates.append(sale_date)
        unit_values.append(price / sqft)

    if len(base["comparables"]) < 3:
        base["uncertainties"].append("At least three recent, source-linked, customer-confirmed arm's-length sales are required.")
    if len(set(comp.get("source_url") for comp in base["comparables"])) != len(base["comparables"]):
        base["uncertainties"].append("Comparable sales need distinct source URLs.")
    if not subject_sqft:
        base["uncertainties"].append("Subject property square footage is missing or uncertain.")
    elif len(base["comparables"]) >= 3:
        estimate = round(statistics.median(unit_values) * subject_sqft)
        base["comparable_value_estimate"] = estimate
        base["estimate_basis"] = "median sale price per square foot × customer-provided subject area; customer review required"
    if not base["customer_requested_value"]:
        base["uncertainties"].append("Customer has not supplied the value they want the county to consider.")

    base["result"] = "uncertain — please check" if base["uncertainties"] else "match"
    base["status"] = "needs_customer_confirmation" if base["uncertainties"] else "ready_for_customer_review"
    if base["result"] == "match":
        base["filing_instructions"] = "Review the county's current instructions, confirm the requested value and comparable selection, sign the county form, and submit it through the county's approved channel before the deadline."
    return base


def render_packet(packet: dict[str, Any], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown = [
        f"# Property tax evidence packet — {packet.get('parcel_id', 'unknown parcel')}",
        "",
        f"Result: **{packet['result']}**",
        f"County: {packet.get('county')}",
        f"As of: {packet.get('as_of')}",
        f"County roll evidence: {packet.get('parcel')}",
        f"Customer requested value: {packet.get('customer_requested_value')}",
        f"Comparable value estimate: {packet.get('comparable_value_estimate', 'uncertain — please check')}",
        "",
        "## Comparable sales",
    ]
    for index, comp in enumerate(packet.get("comparables", []), 1):
        markdown.append(f"{index}. Sale date `{comp['sale_date']['value']}` (page {comp['sale_date']['page']}), price `{comp['sale_price']['value']}` (page {comp['sale_price']['page']}), area `{comp['square_feet']['value']}` (page {comp['square_feet']['page']}); source: {comp['source_url']}; arm's-length status confirmed by customer.")
    markdown += ["", "## Customer review", packet["legal_review_notice"]]
    if packet.get("uncertainties"):
        markdown += ["", "## Please check", *[f"- {item}" for item in packet["uncertainties"]]]
    if packet.get("filing_instructions"):
        markdown += ["", packet["filing_instructions"]]
    target.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return target


def prepare_postcard(record: dict[str, Any], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Render a local proof with the shared mail block; this function never sends mail."""
    sender = str(record.get("sender", "Property Tax Packet Service"))
    first_name = html.escape(str(record.get("name", "Property owner")))
    parcel_id = html.escape(str(record.get("parcel_id", "")))
    source = html.escape(str(record.get("source_url", COUNTY_SOURCE_URL)), quote=True)
    front = f"<article><h1>Cook County assessment packet</h1><p>Prepared by {html.escape(sender)}.</p><p>Parcel reference: {parcel_id}.</p></article>"
    back = f"<article><p>Hello {first_name},</p><p>We prepare customer-reviewed property-tax evidence packets using county public records and recent comparable sales.</p><p>Learn more: <a href=\"{source}\">public source record</a></p><p>From {html.escape(sender)}. This is a private business offer, not a county notice.</p></article>"
    destination = str(output_dir) if output_dir else None
    address = record.get("address", {})
    verification = mail.verify_address(address)
    result = mail.postcard(front, back, address, {"name": sender, **record.get("from_address", {})}, approval_id=None, output_dir=destination)
    result["address_verification"] = verification
    result["external_mail_sent"] = False
    return result


def refresh_roll() -> dict[str, Any]:
    """Refresh the county dataset through the shared government feeds block."""
    return {"source_id": COUNTY_SOURCE, **sync(COUNTY_SOURCE)}


def retention_plan(closed_cases_path: str | Path, *, today: date | None = None) -> dict[str, Any]:
    """List closed-case uploads eligible for removal; this function never deletes files."""
    closed_file = Path(closed_cases_path).expanduser().resolve()
    incoming_root = (Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / "property-tax" / "incoming").resolve()
    records = json.loads(closed_file.read_text(encoding="utf-8")) if closed_file.exists() else []
    now = today or date.today()
    eligible = []
    for case in records:
        if case.get("keep") is True or not case.get("closed_on"):
            continue
        closed_on = _day(case["closed_on"])
        if closed_on is None or (now - closed_on).days < 30:
            continue
        for supplied in case.get("uploads", []):
            path = Path(supplied).expanduser().resolve()
            if not path.is_relative_to(incoming_root):
                raise ValueError(f"retention path must stay under the venture incoming folder: {path}")
            eligible.append({"case_id": str(case.get("case_id", "")), "path": str(path), "exists": path.is_file(), "closed_on": closed_on.isoformat()})
    eligible = [row for row in eligible if row["exists"]]
    digest = hashlib.sha256(json.dumps(eligible, sort_keys=True).encode()).hexdigest()
    return {"as_of": now.isoformat(), "retention_days": 30, "eligible": eligible, "sha256": digest, "deletes_files": False}


def execute_retention(plan_path: str | Path, approval_id: str) -> dict[str, Any]:
    """Delete only files in a reviewed 30-day plan after a non-empty Glacier approval ID."""
    if not approval_id.strip():
        raise ValueError("approval_id is required before deleting customer uploads")
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    eligible = plan.get("eligible", [])
    digest = hashlib.sha256(json.dumps(eligible, sort_keys=True).encode()).hexdigest()
    if digest != plan.get("sha256"):
        raise ValueError("retention plan changed after review; create a new plan and approval")
    incoming_root = (Path(os.environ.get("GLACIER_HOME", "data")) / "ventures" / "property-tax" / "incoming").resolve()
    deleted = []
    for row in eligible:
        path = Path(row["path"]).resolve()
        if not path.is_relative_to(incoming_root):
            raise ValueError(f"retention path must stay under the venture incoming folder: {path}")
        if path.is_file():
            path.unlink()
            deleted.append(str(path))
    return {"deleted": deleted, "approval_id": approval_id.strip(), "plan_sha256": digest}


def prepare_case(case_path: str, output_path: str) -> dict[str, Any]:
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    rows = query(COUNTY_SOURCE)
    packet = build_packet(case, rows)
    target = Path(output_path)
    packet["packet_path"] = str(target)
    packet["instructions_path"] = str(target.with_suffix(".md"))
    rendered = render_packet(packet, target)
    if case.get("signer"):
        packet["signature_request"] = customer.request_signature(str(rendered.with_suffix(".md")), case["signer"])
    if case.get("notice_date") and case.get("deadline"):
        deadlines.add(
            str(case.get("case_id") or case.get("parcel_id")),
            str(case["notice_date"]),
            f"{case['notice_date']}|{case['deadline']}",
            f"{COUNTY} appeal deadline for parcel {case.get('parcel_id')}",
        )
    target.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("refresh-roll")
    case = commands.add_parser("prepare-case")
    case.add_argument("--case", required=True)
    case.add_argument("--output", required=True)
    postcard = commands.add_parser("postcard-preview")
    postcard.add_argument("--record", required=True)
    postcard.add_argument("--output-dir", required=True)
    retention = commands.add_parser("retention-plan")
    retention.add_argument("--closed-cases", required=True)
    retention.add_argument("--output", required=True)
    cleanup = commands.add_parser("execute-cleanup")
    cleanup.add_argument("--plan", required=True)
    cleanup.add_argument("--approval-id", required=True)
    args = parser.parse_args()
    if args.command == "refresh-roll":
        result = refresh_roll()
    elif args.command == "prepare-case":
        result = prepare_case(args.case, args.output)
    elif args.command == "postcard-preview":
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        result = prepare_postcard(record, output_dir=args.output_dir)
    elif args.command == "retention-plan":
        result = retention_plan(args.closed_cases)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        result = execute_retention(args.plan, args.approval_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
