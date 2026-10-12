"""Local-file-first Alabama contractor roster checker.

The Actor never contacts the Alabama board. A customer supplies an export file
and its source/date; this adapter only parses that file and compares exact keys.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE_NAME = "supplied Alabama roster"
ALLOWED_FILE_HOSTS = frozenset({"api.apify.com"})
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_QUERIES = 100
MAX_QUERY_LENGTH = 160
MAX_ROSTER_AGE_DAYS = 365
SOURCE_PAGE = "https://genconbd.alabama.gov/"
LIMITATIONS = (
    "This snapshot only checks the supplied roster as of its stated date. "
    "It is not a real-time license determination, identity match, insurance check, or quality endorsement."
)


class SourceUnavailable(RuntimeError):
    """The user-supplied export could not be read or parsed safely."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def urlopen(request: Request, *, timeout: int):
    """Open user-uploaded files without following redirects off Apify storage."""
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


# Earlier names in each tuple win when synonymous columns are both populated.
# Preserve this explicit precedence: set iteration is not a field-mapping rule.
HEADER_ALIASES = {
    "license_number": ("license_number", "license_no", "license_num", "license", "license_#"),
    "business_name": ("business_name", "company_name", "contractor_name", "name"),
    "address": ("business_address", "mailing_address", "address"),
    "city": ("business_city", "city"),
    "state": ("business_state", "state"),
    "zip_code": ("zip_code", "zipcode", "postal_code", "zip"),
    "status": ("license_status", "status"),
    "expiration_date": ("expiration_date", "expiry_date", "expiration", "expires", "exp_date"),
    "specialty": ("specialty", "classification", "license_type", "type"),
}


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("roster_as_of must be a real calendar date in YYYY-MM-DD format") from exc


def _normalize_license(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _normalize_name(value: str) -> str:
    # Keep letters and numbers from every script. The old ASCII-only expression
    # erased names such as 李氏建设, making every such name compare as empty.
    chars: list[str] = []
    for char in unicodedata.normalize("NFKC", value).casefold():
        if char.isalnum() or unicodedata.category(char).startswith("M"):
            chars.append(char)
        else:
            chars.append(" ")
    return " ".join("".join(chars).split())


def load_roster(path: str | Path) -> list[dict[str, str | None]]:
    return load_roster_text(Path(path).read_text(encoding="utf-8-sig"))


def load_roster_text(csv_text: str) -> list[dict[str, str | None]]:
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("The supplied roster file is empty")
    try:
        reader = csv.reader(io.StringIO(csv_text))
        try:
            fieldnames = next(reader)
        except StopIteration:
            fieldnames = []
        if not fieldnames:
            raise ValueError("The supplied file must be a CSV with a header row")
        source_columns: dict[str, list[tuple[int, str]]] = {}
        for index, source in enumerate(fieldnames):
            if source:
                source_columns.setdefault(_normalize_header(source), []).append((index, source))
        columns: dict[str, list[tuple[int, str]]] = {}
        for target, aliases in HEADER_ALIASES.items():
            sources = [source for alias in aliases for source in source_columns.get(alias, [])]
            if sources:
                columns[target] = sources
        if "license_number" not in columns and "business_name" not in columns:
            raise ValueError("The roster needs a license-number or business-name column")
        records: list[dict[str, str | None]] = []
        for source_row in reader:
            if len(source_row) != len(fieldnames):
                raise ValueError("The supplied roster has a malformed row with missing or extra columns")
            row: dict[str, str | None] = {}
            provenance: dict[str, list[str]] = {}
            conflicts: list[str] = []
            for field, sources in columns.items():
                populated = [(source, (source_row[index] or "").strip())
                             for index, source in sources if (source_row[index] or "").strip()]
                provenance[field] = [source for source, _ in populated]
                row[field] = populated[0][1] if populated else None
                if len({value for _, value in populated}) > 1:
                    conflicts.append(field)
            if "expiration_date" in row:
                raw_expiration = row["expiration_date"]
                row["expiration_date"] = _normalize_expiration(raw_expiration)
                if raw_expiration and row["expiration_date"] is None:
                    conflicts.append("invalid_expiration_date")
            row["_field_provenance"] = provenance  # type: ignore[assignment]
            row["_conflicting_fields"] = conflicts  # type: ignore[assignment]
            if row.get("license_number") or row.get("business_name"):
                records.append(row)
        if not records:
            raise ValueError("The supplied roster has no usable contractor rows")
        return records
    except (csv.Error, UnicodeError) as exc:
        raise ValueError("The supplied roster must be a readable UTF-8 CSV file") from exc


def read_roster_file(file_reference: str) -> str:
    """Read a user-uploaded Apify key-value record, never an arbitrary URL/path."""
    if not isinstance(file_reference, str) or not file_reference.strip():
        raise ValueError("Upload a user-supplied roster CSV file")
    parsed = urlparse(file_reference)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_FILE_HOSTS:
        raise ValueError("Roster uploads must be user-uploaded files stored by Apify")
    headers = {"Accept": "text/csv, application/octet-stream"}
    apify_token = os.getenv("APIFY_TOKEN")
    if apify_token:
        headers["Authorization"] = f"Bearer {apify_token}"
    request = Request(file_reference, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read(MAX_FILE_BYTES + 1)
    except (URLError, TimeoutError, OSError) as exc:
        raise SourceUnavailable("The user-uploaded Apify roster file could not be read") from exc
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Roster CSV files must be 25 MiB or smaller")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Roster CSV must be encoded as UTF-8") from exc


def actor_queries(actor_input: dict[str, object]) -> list[dict[str, object]]:
    queries = actor_input.get("queries")
    if queries is None:
        queries = [{"license_number": actor_input.get("license_number"), "name": actor_input.get("name")}]
    if not isinstance(queries, list) or not 1 <= len(queries) <= MAX_QUERIES:
        raise ValueError(f"queries must contain between 1 and {MAX_QUERIES} lookup objects")
    normalized: list[dict[str, object]] = []
    for item in queries:
        if not isinstance(item, dict):
            raise ValueError("Each query must be an object")
        number = item.get("license_number")
        name = item.get("name")
        if bool(number) == bool(name):
            raise ValueError("Each query must provide exactly one of license_number or name")
        if name and len(str(name).strip()) < 3:
            raise ValueError("Business-name searches must be at least 3 characters")
        value = str(number or name).strip()
        if not value or len(value) > MAX_QUERY_LENGTH:
            raise ValueError(f"Search text must be 1 to {MAX_QUERY_LENGTH} characters")
        if name and len(value) < 3:
            raise ValueError("Business-name searches must be at least 3 characters")
        normalized.append({"license_number": str(number).strip() if number else None,
                           "name": str(name).strip() if name else None})
    return normalized


def lookup_many(
    *,
    roster: list[dict[str, str | None]],
    queries: list[dict[str, object]],
    roster_as_of: str,
    source_url: str,
    checked_at: str | None = None,
) -> list[dict[str, object]]:
    as_of = _date(roster_as_of)
    parsed_source = urlparse(source_url)
    if parsed_source.scheme not in {"http", "https"} or not parsed_source.netloc:
        raise ValueError("source_url must point to the official source or supplied export")
    now = datetime.fromisoformat(checked_at) if checked_at else datetime.now(timezone.utc)
    checked_date = now.date()
    age_days = (checked_date - as_of).days
    if age_days < 0:
        raise ValueError("roster_as_of cannot be in the future")
    stale = age_days > MAX_ROSTER_AGE_DAYS
    results: list[dict[str, object]] = []
    for query in queries:
        number = query.get("license_number")
        name = query.get("name")
        if bool(number) == bool(name):
            raise ValueError("Each query must provide exactly one of license_number or name")
        search_value = str(number or name).strip()
        if not search_value or len(search_value) > MAX_QUERY_LENGTH:
            raise ValueError(f"Search text must be 1 to {MAX_QUERY_LENGTH} characters")
        if name and len(search_value) < 3:
            raise ValueError("Business-name searches must be at least 3 characters")
        comparable_key = "license_number" if number else "business_name"
        if not any(row.get(comparable_key) for row in roster):
            results.append(_uncertain(
                query,
                source_url,
                roster_as_of,
                now.isoformat(timespec="seconds"),
                f"The supplied roster has no {comparable_key.replace('_', ' ')} field for this exact comparison.",
            ))
            continue
        if number:
            key = _normalize_license(search_value)
            found = [row for row in roster if row.get("license_number") and _normalize_license(row["license_number"] or "") == key]
        else:
            key = _normalize_name(search_value)
            found = [row for row in roster if row.get("business_name") and _normalize_name(row["business_name"] or "") == key]
        if stale:
            results.append(_uncertain(query, source_url, roster_as_of, now.isoformat(timespec="seconds"), "The supplied roster is more than 365 days old."))
        elif len(found) > 1:
            results.append(_uncertain(query, source_url, roster_as_of, now.isoformat(timespec="seconds"), "The query matches multiple rows; use an exact license number."))
        elif found:
            row = found[0]
            provenance = row.get("_field_provenance") or {}
            conflicts = row.get("_conflicting_fields") or []
            if conflicts:
                results.append(_uncertain(
                    query, source_url, roster_as_of, now.isoformat(timespec="seconds"),
                    "The matched roster row has conflicting or invalid fields: " + ", ".join(conflicts) + ".",
                    field_provenance=provenance,
                    conflicting_fields=conflicts,
                ))
                continue
            results.append({
                "outcome": "match",
                "verification_state": "verified",
                "roster_presence": "listed",
                "license_number": row.get("license_number"),
                "business_name": row.get("business_name"),
                "status": row.get("status"),
                "expiration_date": _normalize_expiration(row.get("expiration_date")),
                "specialty": row.get("specialty"),
                "source_url": source_url,
                "source_as_of": as_of.isoformat(),
                "checked_at": now.isoformat(timespec="seconds"),
                "limitations": LIMITATIONS,
                "field_provenance": json.dumps(provenance, ensure_ascii=False, sort_keys=True),
            })
        else:
            results.append({
                "outcome": f"no match found in {SOURCE_NAME} as of {as_of.isoformat()}",
                "verification_state": "verified",
                "roster_presence": "not_listed",
                "license_number": str(number) if number else None,
                "business_name": str(name) if name else None,
                "status": None,
                "expiration_date": None,
                "specialty": None,
                "source_url": source_url,
                "source_as_of": as_of.isoformat(),
                "checked_at": now.isoformat(timespec="seconds"),
                "limitations": LIMITATIONS,
            })
    return results


def _normalize_expiration(value: str | None) -> str | None:
    if not value:
        return None
    for pattern in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _uncertain(query: dict[str, object], source_url: str, roster_as_of: str,
               checked_at: str, reason: str, *,
               field_provenance: object | None = None,
               conflicting_fields: object | None = None) -> dict[str, object]:
    return {
        "outcome": "uncertain — please check",
        "verification_state": "unverifiable",
        "roster_presence": "uncertain",
        "license_number": query.get("license_number"),
        "business_name": query.get("name"),
        "status": None,
        "expiration_date": None,
        "specialty": None,
        "source_url": source_url,
        "source_as_of": roster_as_of,
        "checked_at": checked_at,
        "limitations": f"{LIMITATIONS} {reason}",
        "field_provenance": json.dumps(field_provenance or {}, ensure_ascii=False, sort_keys=True),
        "conflicting_fields": ", ".join(conflicting_fields or []),
    }


def outage_result(query: dict[str, object], source_url: str, roster_as_of: str,
                  checked_at: str, reason: str) -> dict[str, object]:
    """Create a customer-facing uncertainty result when the supplied file is unavailable."""
    return _uncertain(query, source_url, roster_as_of, checked_at,
                      f"The supplied roster could not be read: {reason}")
