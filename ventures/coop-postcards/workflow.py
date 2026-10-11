"""Co-op claim checks wired to Glacier's shared reader, rules and deadlines."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any
import re
import hashlib
import textwrap
import zlib

from ventures.blocks.mail import postcard
from ventures.blocks.connectors import JobberClient


BRAND_RULES_PATH = Path(__file__).resolve().parent / "brand-rules.json"
# Public, source-linked records for integrations that need a quick brand lookup.
# These are pointers for owner review, not authority to approve or file a claim.
BRAND_RULES = {
    record["brand"].casefold(): {
        **record,
        "status": record.get("rule_status", "unverified"),
        "verified": record.get("rule_status") == "verified",
    }
    for record in json.loads(BRAND_RULES_PATH.read_text(encoding="utf-8"))
}
COOP_RULES = BRAND_RULES
EVIDENCE_CHECKLIST = (
    ("dealer_authorization", "Dealer authorization for this specific claim"),
    ("program_preapproval", "Brand pre-approval, if required by the confirmed current program"),
    ("ad_proof", "Final advertisement proof showing brand and dealer attribution"),
    ("itemized_invoice", "Itemized invoice for the advertising expense"),
    ("proof_of_payment", "Proof the invoice was paid"),
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def claim_reminder_dates(expires_on: str) -> list[date]:
    expiry = _parse_date(expires_on)
    return [expiry - timedelta(days=60), expiry - timedelta(days=30)]


def load_brand_rules(path: str | Path = BRAND_RULES_PATH) -> dict[str, dict[str, Any]]:
    """Load source-linked program records; unverified records never authorize filing."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(record["brand"]).casefold(): record for record in records}


def completed_jobber_jobs(client: JobberClient | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Read completed jobs from the connected Jobber account without mutations."""
    jobber = client or JobberClient()
    account = jobber.test_connection()
    rows = jobber.get_jobs(max_pages=5)
    complete = [row for row in rows if str(row.get("jobStatus", "")).casefold() in {"completed", "complete"}]
    return str(account.get("account") or "Jobber dealer"), complete


def _claim_id(job: dict[str, Any]) -> str:
    raw = str(job.get("id") or job.get("jobNumber") or "")
    if not raw:
        raise ValueError("Jobber job needs an id or job number")
    return "jobber-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _claim_markdown(draft: dict[str, Any]) -> str:
    checklist = "\n".join(
        f"- [{'x' if item['present'] else ' '}] {item['label']}"
        for item in draft["evidence_checklist"]
    )
    reminders = draft.get("reminder_dates") or []
    reminder_text = ", ".join(reminders) if reminders else "Pending confirmation of current program expiry"
    source = draft.get("brand_rule") or {}
    rule_url = source.get("source_url", "")
    rule_status = source.get("rule_status", "unverified")
    return (
        f"# Co-op claim draft — {draft['claim_id']}\n\n"
        "**Draft only. Not filed, not approved by the brand, and not proof of eligibility.**\n\n"
        f"- Dealer account: {draft['dealer_label']}\n"
        f"- Jobber job: {draft['job_number']} — {draft['job_title']}\n"
        f"- Completed: {draft.get('completed_at') or 'not supplied by Jobber'}\n"
        f"- Brand: {draft.get('brand') or 'needs dealer confirmation'}\n"
        f"- Rule status: {rule_status}\n"
        f"- Rule source: {rule_url or 'no brand selected'}\n"
        f"- Program expiry: {draft.get('expires_on') or 'needs dealer confirmation'}\n"
        f"- Reminder dates: {reminder_text}\n"
        f"- Job source: {draft.get('job_source') or 'Jobber read-only connector'}\n\n"
        "## Evidence checklist\n\n" + checklist + "\n\n"
        "## Brand rule notes\n\n"
        f"{source.get('program_summary', 'Select and confirm the applicable brand program.')}.\n\n"
        "**The evidence checklist is a starting point. Exact brand requirements are unverified until the owner confirms the current dealer program terms.**\n\n"
        "## Owner steps\n\n"
        "1. Confirm the applicable current program terms, eligibility, deadline, and required evidence with the brand.\n"
        "2. Obtain dealer authorization and complete/sign/file the claim yourself. Glacier does not submit it.\n"
    )


def _write_claim_pdf(markdown: str, path: Path) -> None:
    """Create a one-page, US-letter PDF using the standard library only."""
    lines: list[str] = []
    for paragraph in markdown.splitlines():
        stripped = paragraph.replace("**", "").replace("`", "").replace("#", "").strip()
        lines.extend(textwrap.wrap(stripped, width=92) or ([""] if not stripped else []))
    lines = lines[:54]
    commands = ["BT", "/F1 9 Tf", "48 744 Td"]
    for i, line in enumerate(lines):
        if i:
            commands.append("0 -13 Td")
        escaped = line.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    stream = zlib.compress("\n".join(commands).encode("latin-1", "replace"))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} /Filter /FlateDecode >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    # A binary marker follows the header as recommended by the PDF format;
    # this also keeps valid xref padding from appearing as text whitespace.
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


def generate_claim_draft(
    job: dict[str, Any], dealer_label: str, *, details: dict[str, Any] | None = None,
    output_dir: str | Path, rules_path: str | Path = BRAND_RULES_PATH,
) -> dict[str, Any]:
    """Write a local markdown/PDF draft from one completed Jobber job; never files it."""
    if str(job.get("jobStatus", "")).casefold() not in {"completed", "complete"}:
        raise ValueError("only completed Jobber jobs can start a co-op claim draft")
    details = details or {}
    brand = str(details.get("brand") or "").strip().casefold()
    rule = load_brand_rules(rules_path).get(brand) if brand else None
    expiry = str(details.get("expires_on") or (rule or {}).get("expires_on") or "").strip()
    try:
        reminders = [day.isoformat() for day in claim_reminder_dates(expiry)] if expiry else []
    except ValueError:
        reminders = []
        expiry = ""
    docs = set(str(item) for item in details.get("evidence", []))
    checklist = [{"key": key, "label": label, "present": key in docs} for key, label in EVIDENCE_CHECKLIST]
    claim_id = _claim_id(job)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    draft = {
        "claim_id": claim_id,
        "dealer_label": dealer_label or "Jobber dealer",
        "job_id": str(job.get("id") or ""),
        "job_number": str(job.get("jobNumber") or "(unknown)"),
        "job_title": str(job.get("title") or "Completed job"),
        "completed_at": str(job.get("completedAt") or ""),
        "job_source": str(job.get("jobberWebUri") or "Jobber read-only connector"),
        "brand": brand or None,
        "brand_rule": rule,
        "rule_status": (rule or {}).get("rule_status", "unverified"),
        "expires_on": expiry or None,
        "reminder_dates": reminders,
        "deadline_status": "scheduled from confirmed expiry" if expiry else "pending confirmation of current program expiry",
        "evidence_checklist": checklist,
        "filing_ready": False,
        "external_action": "owner only; no filing performed",
    }
    markdown = _claim_markdown(draft)
    md_path = root / f"{claim_id}.md"
    pdf_path = root / f"{claim_id}.pdf"
    json_path = root / f"{claim_id}.json"
    md_path.write_text(markdown, encoding="utf-8")
    _write_claim_pdf(markdown, pdf_path)
    draft.update({"markdown_path": str(md_path), "pdf_path": str(pdf_path), "record_path": str(json_path)})
    json_path.write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if expiry:
        from ventures.blocks.deadlines import add as add_deadline
        first_reminder = claim_reminder_dates(expiry)[0]
        add_deadline(claim_id, first_reminder.isoformat(), "0d|30d", f"{brand.title()} co-op claim expiry")
    return draft


def prepare_claim_draft(job: dict[str, Any], *, output_dir: str | Path) -> dict[str, Any]:
    """Create a safe draft from a compact Jobber intake record.

    This adapter accepts job-shaped input used by local integrations and fixtures.
    It copies only claim-relevant fields; Jobber client/property/custom-field payloads
    are deliberately excluded from all generated artifacts.
    """
    job_id = str(job.get("id") or job.get("job_id") or job.get("jobNumber") or "")
    if not job_id:
        raise ValueError("Jobber job needs an id or job number")
    status = str(job.get("jobStatus", job.get("status", "completed"))).casefold()
    if status not in {"completed", "complete"}:
        raise ValueError("only completed Jobber jobs can start a co-op claim draft")

    safe_job = {
        "id": job_id,
        "jobNumber": job.get("jobNumber") or job.get("job_number") or job_id,
        "title": job.get("title") or "Completed job",
        "jobStatus": "COMPLETED",
        "completedAt": job.get("completedAt") or job.get("completed_at"),
        "jobberWebUri": job.get("jobberWebUri") or job.get("source_url"),
    }
    evidence = list(job.get("evidence") or [])
    if job.get("invoice"):
        evidence.append("itemized_invoice")
    details = {
        "brand": job.get("brand"),
        "program_year": job.get("program_year"),
        "expires_on": job.get("expires_on"),
        "evidence": evidence,
        "dealer_authorized": job.get("dealer_authorized"),
        "preapproval_id": job.get("preapproval_id"),
        "installed_on": job.get("installed_on"),
    }
    draft = generate_claim_draft(
        safe_job,
        str(job.get("dealer_label") or "Jobber dealer"),
        details=details,
        output_dir=output_dir,
    )
    # Preserve the year and invoice reference for the owner, without treating
    # either as proof of the missing ad/payment records or current program terms.
    draft["program_year"] = str(job.get("program_year") or "") or None
    draft["invoice_reference"] = str(job.get("invoice") or "") or None
    if not draft.get("reminder_dates"):
        draft["reminders"] = [
            f"Confirm the current {draft.get('brand') or 'brand'} program deadline for {draft.get('program_year') or 'the applicable program year'}"
        ]
    else:
        draft["reminders"] = list(draft["reminder_dates"])
    Path(draft["record_path"]).write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return draft


def _claim_state_path(claim_id: str, state_dir: str | Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", claim_id):
        raise ValueError("claim_id must contain only letters, numbers, hyphens, and underscores")
    return Path(state_dir) / f"{claim_id}.json"


def _save_claim_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def begin_claim_attempt(claim_id: str, state_dir: str | Path) -> dict[str, Any]:
    """Start the original filing or the single corrected resubmit after rejection."""
    path = _claim_state_path(claim_id, state_dir)
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"claim_id": claim_id, "attempts": 0, "status": "not_started"}
    if state["status"] == "not_started" and state["attempts"] == 0:
        state.update(attempts=1, status="in_progress")
    elif state["status"] == "corrected_resubmit_available" and state["attempts"] == 1:
        state.update(attempts=2, status="in_progress")
    else:
        raise ValueError(f"claim is {state['status']}; another submission attempt is not allowed")
    _save_claim_state(path, state)
    return state


def record_claim_outcome(claim_id: str, outcome: str, state_dir: str | Path, *, reason: str = "", owner_filed: bool = False) -> dict[str, Any]:
    """Record an owner-reported portal outcome and allow at most one correction."""
    path = _claim_state_path(claim_id, state_dir)
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
    elif owner_filed:
        state = {"claim_id": claim_id, "attempts": 1, "status": "in_progress", "owner_reported_filing": True}
    else:
        raise ValueError("no recorded attempt; confirm --owner-filed after you personally submit the claim")
    if state["status"] != "in_progress":
        raise ValueError(f"claim is {state['status']}; no outcome can be recorded")
    if outcome == "accepted":
        state.update(status="accepted", outcome_reason=reason.strip())
    elif outcome == "rejected":
        if not reason.strip():
            raise ValueError("rejection reason is required")
        status = "corrected_resubmit_available" if state["attempts"] == 1 else "dropped"
        state.update(status=status, outcome_reason=reason.strip())
    else:
        raise ValueError("outcome must be accepted or rejected")
    _save_claim_state(path, state)
    return state


def _read_evidence(fields: dict[str, Any], documents: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not documents:
        return fields, []
    from ventures.blocks.reader import read_document

    combined = dict(fields)
    sources: list[dict[str, Any]] = []
    for path in documents:
        result = read_document(path)
        extracted = result.get("fields", {}) if isinstance(result, dict) else {}
        sources.append({"document": str(path), "fields": extracted})
        for name, field in extracted.items():
            combined.setdefault(name, field)
    return combined, sources


def _plain(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def check_claim(
    fields: dict[str, Any], rules: dict[str, Any], *, evidence_documents: list[str] | None = None,
    claim_id: str | None = None,
) -> dict[str, Any]:
    """Run co-op fields through the shared rules block and apply business guards."""
    if not rules or not isinstance(rules.get("required_evidence"), list) or not rules.get("program_year"):
        return {"verdict": "uncertain", "filing_ready": False, "issues": ["brand program rules are missing or incomplete"]}
    issues: list[str] = []
    sources: list[dict[str, Any]] = []
    try:
        fields, sources = _read_evidence(fields, evidence_documents or [])
    except (OSError, ValueError, ImportError) as exc:
        return {"verdict": "uncertain", "filing_ready": False,
                "issues": [f"claim evidence could not be read: {exc}"], "reminders": []}
    try:
        expiry = _parse_date(str(rules["expires_on"]))
        reminders = [day.isoformat() for day in claim_reminder_dates(str(rules["expires_on"]))]
    except (KeyError, ValueError):
        return {"verdict": "uncertain", "filing_ready": False, "issues": ["brand program expiry date is missing or invalid"], "reminders": []}
    if expiry < date.today():
        return {"verdict": "fail", "filing_ready": False, "issues": ["brand program year has expired"], "reminders": reminders}
    if str(fields.get("program_year", "")) != str(rules["program_year"]):
        issues.append("program year does not match the brand rules")
    for name in rules["required_evidence"]:
        value = _plain(fields.get(name))
        if not value or (isinstance(fields.get(name), dict) and fields[name].get("uncertain")):
            issues.append(f"required evidence is missing: {name}")
    if rules.get("requires_preapproval") and not fields.get("preapproval_id"):
        issues.append("required brand pre-approval is missing")
    if not fields.get("dealer_authorized"):
        issues.append("dealer authorization is required")
    if issues:
        return {"verdict": "fail", "filing_ready": False, "issues": issues, "reminders": reminders, "sources": sources}
    try:
        from ventures.blocks.rules import check as check_rules
        from ventures.blocks.deadlines import add as add_deadline
    except ImportError:
        return {"verdict": "uncertain", "filing_ready": False, "issues": ["shared rules or deadline tracker is not installed; claim cannot be filed"], "reminders": reminders, "sources": sources}
    required = list(dict.fromkeys([*rules["required_evidence"], "program_year"]))
    checker_fields = {name: _plain(fields.get(name)) for name in required}
    rule_spec = {
        "title": "Brand co-op program rules",
        "source": {"title": str(rules.get("brand", "Brand program rules")), "url": str(rules.get("source_url", ""))},
        "rules": [{"id": f"coop.{name}", "field": name, "check": "non_empty",
                   "failure": f"Provide {name} from the brand program record."} for name in required],
    }
    verdict = check_rules(checker_fields, rule_spec)
    if verdict.get("verdict") != "pass":
        return {"verdict": verdict.get("verdict", "uncertain"), "filing_ready": False,
                "issues": verdict.get("results", []), "reminders": reminders, "sources": sources}
    if claim_id:
        add_deadline(claim_id, reminders[0], "0d|30d", f"Co-op program expiry: {rules.get('brand', 'brand claim')}")
    return {"verdict": "pass", "filing_ready": True, "issues": [], "reminders": reminders,
            "sources": sources, "rules_check": verdict}


def check_route_card(card: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    campaign_id = str(card.get("campaign_id", ""))
    if not campaign_id or not campaign_id.replace("-", "").replace("_", "").isalnum():
        issues.append("a stable campaign_id is required to prevent duplicate mail")
    if not card.get("campaign_id"):
        issues.append("a stable campaign ID is required to prevent duplicate mail")
    if not card.get("town") or not card.get("route_id") or not card.get("fill_by"):
        issues.append("town, route, and fill-by date are required")
    else:
        try:
            if _parse_date(str(card["fill_by"])).month != 11:
                issues.append("year-end dealer card fill-by date must be in November")
        except ValueError:
            issues.append("fill-by date must be an ISO date")
    if not isinstance(card.get("from"), dict) or not card["from"].get("name"):
        issues.append("a clearly named sender is required")
    if not isinstance(card.get("to"), dict) or not card["to"].get("address_line1"):
        issues.append("a business recipient street address is required")
    mailpiece = card.get("mailpiece")
    if not isinstance(mailpiece, dict):
        issues.append("USPS EDDM size and weight details are required")
    else:
        try:
            length = float(mailpiece["length_inches"])
            height = float(mailpiece["height_inches"])
            thickness = float(mailpiece["thickness_inches"])
            weight = float(mailpiece["weight_ounces"])
            if not (3.5 <= length <= 15 and 3.5 <= height <= 12 and height <= length):
                issues.append("USPS EDDM Retail dimensions must be 3.5–15 inches long and 3.5–12 inches high, with height no greater than length")
            if not 0.007 <= thickness <= 0.75:
                issues.append("USPS EDDM Retail thickness must be 0.007–0.75 inches")
            if weight <= 0 or weight > 3.3:
                issues.append("USPS EDDM Retail weight must be greater than 0 and no more than 3.3 ounces")
            if not (length > 10.5 or height > 6.125 or thickness > 0.25):
                issues.append("USPS EDDM Retail mailpiece must be longer than 10.5 inches, higher than 6.125 inches, or thicker than 0.25 inches")
        except (KeyError, TypeError, ValueError):
            issues.append("USPS EDDM size and weight values must be numeric inches and ounces")
    categories: set[str] = set()
    for buyer in card.get("buyers", []):
        category = str(buyer.get("category", "")).strip().casefold()
        if not buyer.get("written_approval"):
            issues.append(f"written buyer approval is missing for {category or 'an ad'}")
        if category and category in categories:
            issues.append(f"duplicate category: {category}")
        categories.add(category)
    for job in card.get("street_jobs", []):
        if job.get("homeowner_name") or job.get("recipient_name"):
            issues.append("homeowner name must not appear on street postcards")
        if not job.get("address"):
            issues.append("street-level job address is required")
    return {"verdict": "fail" if issues else "pass", "issues": issues}


def render_postcard(record: dict[str, Any]) -> tuple[str, str]:
    """Return neutral, clearly branded EDDM Retail flat markup (11.5 x 6.25 in)."""
    sender = str(record.get("sender") or "Glacier Co-op & Street Cards")
    dealer = str(record.get("dealer_name") or "local dealer")
    town = str(record.get("town") or "your neighborhood")
    street = str(record.get("street") or "")
    front = (
        '<main style="width:11.5in;height:6.25in"><h1>Local businesses for ' + _escape(town) + '</h1>'
        '<p>Advertising from ' + _escape(sender) + '</p><p>Your ad here</p></main>'
    )
    back = (
        '<main style="width:11.5in;height:6.25in"><h2>' + _escape(dealer) + '</h2><p>Serving ' + _escape(town) + '</p>'
        '<p>From ' + _escape(sender) + '</p>'
        + ('<p>Recent work near ' + _escape(street) + '</p>' if street else '')
        + '<p>Ask us about this offer. No homeowner names are used.</p></main>'
    )
    return front, back


def _escape(value: str) -> str:
    import html
    return html.escape(value, quote=True)


def send_postcard_file(path: str | Path, output_dir: str | Path | None = None) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    front, back = render_postcard(record.get("proof_record", record))
    return postcard(
        front,
        back,
        record["to"],
        record["from"],
        **({"output_dir": output_dir} if output_dir else {}),
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description="Co-op claim and postcard workflow tools")
    sub = parser.add_subparsers(dest="action", required=True)
    render = sub.add_parser("postcard", help="render or send a supplied card in Lob test mode")
    render.add_argument("record", help="JSON with dealer/town, recipient and sender details")
    render.add_argument("--output-dir")
    args = parser.parse_args()
    if args.action == "postcard":
        result = send_postcard_file(args.record, args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
