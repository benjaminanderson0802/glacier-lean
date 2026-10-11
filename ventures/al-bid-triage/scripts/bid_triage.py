"""Local-only triage for notice details supplied by a contractor."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


REQUIRED_FIELDS = (
    "notice_number",
    "project",
    "advertising_agency",
    "county",
    "municipality",
    "bid_date",
    "prebid_meeting",
    "description",
    "official_url",
    "source_mode",
    "received_at",
)
ALLOWED_SOURCE_MODES = {"forwarded_official_notice", "owner_supplied_link", "official_export"}
TRADE_TERMS = {
    "electrical": ("electrical", "electrician", "power panel", "wiring", "generator"),
    "roofing": ("roof", "roofing", "reroof"),
    "grading": ("grading", "grade and drain", "earthwork", "site preparation"),
    "fencing": ("fence", "fencing", "guardrail"),
    "general-contracting": ("general contractor", "commercial building", "building construction", "public works"),
}


def read_notices(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in REQUIRED_FIELDS):
            missing = sorted(set(REQUIRED_FIELDS) - set(reader.fieldnames or []))
            raise ValueError(f"input is missing required fields: {', '.join(missing)}")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            normalized = {key: (row.get(key) or "").strip() for key in REQUIRED_FIELDS}
            if not normalized["notice_number"] or not normalized["project"]:
                raise ValueError(f"row {line_number} needs a notice number and project title")
            parsed_url = urlparse(normalized["official_url"])
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise ValueError(f"row {line_number} source must be an https URL")
            if normalized["source_mode"] not in ALLOWED_SOURCE_MODES:
                raise ValueError(f"row {line_number} source mode is not allowed")
            rows.append(normalized)
    return rows


def _date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid date: {value}") from exc


def _matches_trade(row: dict[str, str], trade: str) -> bool:
    terms = TRADE_TERMS.get(trade.casefold())
    if not terms:
        raise ValueError(f"unsupported trade '{trade}'; choose one of: {', '.join(TRADE_TERMS)}")
    searchable = f"{row['project']} {row['description']}".casefold()
    return any(term in searchable for term in terms)


def build_digest(
    notices: Iterable[dict[str, str]], trade: str, counties: set[str], as_of: str
) -> dict:
    cutoff = _date(as_of)
    if cutoff is None:
        raise ValueError("as_of date is required")
    normalized_counties = {county.strip().casefold() for county in counties}
    if not normalized_counties:
        raise ValueError("select at least one county")

    matches = []
    seen = set()
    for row in notices:
        number = row["notice_number"].strip()
        if number in seen:
            continue
        seen.add(number)
        if row["county"].strip().casefold() not in normalized_counties:
            continue
        if not _matches_trade(row, trade):
            continue
        due = _date(row["bid_date"])
        if due is not None and due < cutoff:
            continue
        match = dict(row)
        match["deadline_status"] = (
            "uncertain — check controlling notice" if due is None else "upcoming — verify with issuing authority"
        )
        match["next_action"] = (
            "Open the issuing authority's notice and confirm deadline, addenda, eligibility, and bid instructions."
        )
        matches.append(match)

    source_mode = (
        "user_supplied_fixture"
        if any(urlparse(row["official_url"]).hostname.endswith(".example") for row in matches)
        else "user_supplied"
    )
    return {
        "as_of": cutoff.isoformat(),
        "trade": trade.casefold(),
        "counties": sorted(county.title() for county in normalized_counties),
        "source_mode": source_mode,
        "matches": matches,
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Alabama public works bid triage",
        "",
        f"Prepared: {result['as_of']}",
        f"Filter: {result['trade']} | {', '.join(result['counties'])} counties",
        f"Input: {result['source_mode']}",
        "",
        (
            "Sample provenance: synthetic rows from `tests/fixtures/sample-general-contracting.csv`; "
            "not fetched from Alabama Builds. The intended official listing source is "
            "https://alabamabuilds.gov/AdvertisementBids (research checked 2026-10-10)."
            if result["source_mode"] == "user_supplied_fixture"
            else "Source details were supplied by the user; verify each URL and controlling notice before relying on it."
        ),
        "",
        "This is a discovery aid, not a complete bid record. The issuing authority's notice controls. "
        "Confirm deadlines, addenda, qualifications, and instructions at the source before acting.",
        "",
    ]
    if not result["matches"]:
        lines.extend(["No notices matched these filters.", ""])
        return "\n".join(lines)

    for item in result["matches"]:
        due = item["bid_date"] or "Not supplied"
        prebid = item["prebid_meeting"] or "Not supplied"
        lines.extend([
            f"## {item['project']}",
            "",
            f"- Notice: {item['notice_number']}",
            f"- Issuer: {item['advertising_agency']} ({item['municipality']}, {item['county']} County)",
            f"- Bid due: {due} — {item['deadline_status']}",
            f"- Pre-bid meeting: {prebid}",
            f"- Scope notes: {item['description'] or 'Not supplied'}",
            f"- Next action: {item['next_action']}",
            f"- Official notice: {item['official_url']}",
            "",
        ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage owner-supplied official bid notice details.")
    parser.add_argument("--input", required=True, help="CSV of forwarded official notice fields or owner-supplied links")
    parser.add_argument("--trade", required=True, choices=sorted(TRADE_TERMS))
    parser.add_argument("--counties", required=True, help="Comma-separated Alabama counties")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Date to evaluate deadlines against (YYYY-MM-DD)")
    parser.add_argument("--output", required=True, help="Write the digest to this local Markdown file")
    args = parser.parse_args(argv)
    try:
        result = build_digest(
            read_notices(args.input), args.trade, set(args.counties.split(",")), args.as_of
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
