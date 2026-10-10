"""Co-op claim checks wired to Glacier's shared reader, rules and deadlines."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ventures.blocks.mail import postcard


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def claim_reminder_dates(expires_on: str) -> list[date]:
    expiry = _parse_date(expires_on)
    return [expiry - timedelta(days=60), expiry - timedelta(days=30)]


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
