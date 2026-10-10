"""Venture-specific checks and adapters for shared co-op/mail blocks.

The document reader, rules checker, and deadline block are still being built by
their owners. This module does not replace those shared blocks: it keeps the
venture's hand-entered readiness checks explicit until those interfaces land.
"""
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


def check_claim(fields: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Run co-op fields through the shared rules block and apply business guards."""
    if not rules or not isinstance(rules.get("required_evidence"), list) or not rules.get("program_year"):
        return {"verdict": "uncertain", "filing_ready": False, "issues": ["brand program rules are missing or incomplete"]}
    issues: list[str] = []
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
        if not fields.get(name):
            issues.append(f"required evidence is missing: {name}")
    if rules.get("requires_preapproval") and not fields.get("preapproval_id"):
        issues.append("required brand pre-approval is missing")
    if not fields.get("dealer_authorized"):
        issues.append("dealer authorization is required")
    if issues:
        return {"verdict": "fail", "filing_ready": False, "issues": issues, "reminders": reminders}
    try:
        from ventures.blocks.rules import check as check_rules
    except ImportError:
        return {"verdict": "uncertain", "filing_ready": False, "issues": ["shared rules checker is not installed; claim cannot be filed"], "reminders": reminders}
    verdict = check_rules(fields, rules)
    if verdict.get("verdict") != "pass":
        return {"verdict": verdict.get("verdict", "uncertain"), "filing_ready": False, "issues": verdict.get("results", []), "reminders": reminders}
    return {"verdict": "pass", "filing_ready": True, "issues": [], "reminders": reminders}


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
    """Return neutral, clearly branded 6x4 Lob postcard markup."""
    sender = str(record.get("sender") or "Glacier Co-op & Street Cards")
    dealer = str(record.get("dealer_name") or "local dealer")
    town = str(record.get("town") or "your neighborhood")
    street = str(record.get("street") or "")
    front = (
        '<main><h1>Local businesses for ' + _escape(town) + '</h1>'
        '<p>Advertising from ' + _escape(sender) + '</p><p>Your ad here</p></main>'
    )
    back = (
        '<main><h2>' + _escape(dealer) + '</h2><p>Serving ' + _escape(town) + '</p>'
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
