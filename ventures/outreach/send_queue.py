#!/usr/bin/env python3
"""Validate a prepared outreach CSV and render data for manual Gmail drafts.

This script has no mail, browser, or network integration and never sends.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


SENDER_NAME = "Benjamin Anderson"
SENDER_EMAIL = "ben@andersoneducation.us"
ALLOWED_PLACEHOLDER = "{{POSTAL_ADDRESS}}"
REQUIRED_COLUMNS = (
    "venture",
    "business",
    "contact_email",
    "contact_form_url",
    "contact_source_url",
    "subject",
    "body",
    "followup_subject",
    "followup_body",
)
SUPPRESSION_COLUMNS = ("contact_email", "business")
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
WORD_RE = re.compile(r"\b[\w]+(?:[’'-][\w]+)*\b", re.UNICODE)
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")


@dataclass
class ValidationResult:
    rows: list[dict[str, str]]
    errors: list[str]

    @property
    def valid(self) -> bool:
        return not self.errors


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            missing = [column for column in REQUIRED_COLUMNS if column not in columns]
            if missing:
                return [], ["missing required columns: " + ", ".join(missing)]
            return [
                {key: (value or "").strip() for key, value in row.items() if key is not None}
                for row in reader
            ], []
    except OSError as exc:
        return [], [f"cannot read CSV: {exc}"]


def _read_suppression(path: Path | None) -> tuple[set[str], set[str], list[str]]:
    if path is None:
        return set(), set(), []
    if not path.exists():
        return set(), set(), [f"suppression file does not exist: {path}"]
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in SUPPRESSION_COLUMNS if column not in (reader.fieldnames or [])]
            if missing:
                return set(), set(), ["suppression.csv missing required columns: " + ", ".join(missing)]
            emails = set()
            businesses = set()
            for row in reader:
                email = (row.get("contact_email") or "").strip().casefold()
                business = (row.get("business") or "").strip().casefold()
                reason = (row.get("reason") or "").strip().casefold()
                last_sent = (row.get("last_sent_at") or "").strip()
                recent = False
                if last_sent:
                    try:
                        sent_on = date.fromisoformat(last_sent[:10])
                        recent = 0 <= (date.today() - sent_on).days < 7
                    except ValueError:
                        return set(), set(), [f"invalid last_sent_at in suppression.csv: {last_sent}"]
                permanently_suppressed = not last_sent or reason in {"opt_out", "declined", "suppressed"}
                if permanently_suppressed or recent:
                    if email:
                        emails.add(email)
                    if business:
                        businesses.add(business)
            return emails, businesses, []
    except OSError as exc:
        return set(), set(), [f"cannot read suppression.csv: {exc}"]


def validate_csv(path: str | Path, suppression_path: str | Path | None = None) -> ValidationResult:
    """Return all CSV validation errors without writing or sending anything."""
    csv_path = Path(path)
    rows, errors = _read_csv(csv_path)
    if errors:
        return ValidationResult([], errors)

    suppressed_emails, suppressed_businesses, suppression_errors = _read_suppression(
        Path(suppression_path) if suppression_path is not None else None
    )
    errors.extend(suppression_errors)
    seen_businesses: set[str] = set()
    seen_emails: set[str] = set()

    for index, row in enumerate(rows, start=2):
        prefix = f"row {index}: "
        business = row.get("business", "").strip()
        email = row.get("contact_email", "").strip().casefold()
        form_url = row.get("contact_form_url", "").strip()
        source_url = row.get("contact_source_url", "").strip()
        business_key = re.sub(r"\s+", " ", business.casefold())

        for column in REQUIRED_COLUMNS:
            if not row.get(column, "").strip() and column not in ("contact_email", "contact_form_url"):
                errors.append(prefix + f"{column} is required")
        if not email and not form_url:
            errors.append(prefix + "a public contact email or contact form URL is required")
        if email and not EMAIL_RE.fullmatch(email):
            errors.append(prefix + "contact_email is not a valid email address")
        if form_url and not URL_RE.fullmatch(form_url):
            errors.append(prefix + "contact_form_url must be an http(s) URL")
        if not URL_RE.fullmatch(source_url):
            errors.append(prefix + "contact_source_url must be an http(s) URL")

        if business_key:
            if business_key in seen_businesses:
                errors.append(prefix + f"duplicate business in weekly queue: {business}")
            seen_businesses.add(business_key)
        if email:
            if email in seen_emails:
                errors.append(prefix + f"duplicate contact email in weekly queue: {email}")
            seen_emails.add(email)

        if email in suppressed_emails or business_key in suppressed_businesses:
            errors.append(prefix + "contact is suppressed or was contacted in the past 7 days")

        for column in REQUIRED_COLUMNS:
            value = row.get(column, "")
            placeholders = [p for p in PLACEHOLDER_RE.findall(value) if p != ALLOWED_PLACEHOLDER]
            if placeholders:
                errors.append(prefix + f"unexpected placeholder in {column}: {', '.join(sorted(set(placeholders)))}")
        for column in ("body", "followup_body"):
            words = len(WORD_RE.findall(row.get(column, "")))
            if words >= 120:
                errors.append(prefix + f"{column} must be under 120 words (found {words})")

    return ValidationResult(rows, errors)


def to_gmail_drafts(result: ValidationResult) -> dict[str, Any]:
    """Convert valid rows to draft-ready JSON; contact-form rows remain manual."""
    if not result.valid:
        raise ValueError("cannot create draft JSON from an invalid queue")
    email_drafts: list[dict[str, str]] = []
    contact_form_queue: list[dict[str, str]] = []
    for row in result.rows:
        item = {
            "venture": row["venture"],
            "business": row["business"],
            "to": row["contact_email"],
            "contact_form_url": row["contact_form_url"],
            "contact_source_url": row["contact_source_url"],
            "from_name": SENDER_NAME,
            "from_email": SENDER_EMAIL,
            "subject": row["subject"],
            "body_text": row["body"],
            "followup": {
                "subject": row["followup_subject"],
                "body_text": row["followup_body"],
                "not_before_day": 5,
                "requires_manual_review": True,
            },
        }
        if row["contact_email"]:
            email_drafts.append(item)
        else:
            contact_form_queue.append(item)
    return {
        "mode": "drafts_only",
        "sends_enabled": False,
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "email_drafts": email_drafts,
        "contact_form_queue": contact_form_queue,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path(__file__).with_name("batch-2026-10-11.csv"))
    parser.add_argument("--suppression", type=Path, default=Path(__file__).with_name("suppression.csv"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("gmail-drafts-2026-10-11.json"))
    args = parser.parse_args(argv)

    result = validate_csv(args.csv, args.suppression)
    if not result.valid:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(to_gmail_drafts(result), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}; {len(result.rows)} draft records prepared, no messages sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
