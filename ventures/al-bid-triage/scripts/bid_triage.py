"""Local-only triage for notice details supplied by a contractor."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
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
            if normalized["received_at"]:
                _received_at(normalized)
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


def _received_at(row: dict[str, str]) -> datetime | None:
    """Parse supplied revision provenance without inventing an ordering."""
    value = row.get("received_at", "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(value), datetime.min.time())
        except ValueError as exc:
            raise ValueError(f"invalid received_at timestamp: {value}") from exc
    # Preserve whether the supplier gave a timezone. Mixed naive and aware
    # timestamps are treated as ambiguous by the caller.
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)
    return parsed


def _revision_groups(notices: Iterable[dict[str, str]]) -> list[tuple[dict[str, str], list[dict[str, str]], bool]]:
    """Return the latest supplied row per issuer/notice, preserving its history.

    A timestamp tie between materially different supplied versions is ambiguous;
    keep all tied rows so renderers can show the conflict instead of choosing one.
    """
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for index, source_row in enumerate(notices):
        row = dict(source_row)
        agency = row["advertising_agency"].strip().casefold()
        # A missing issuer cannot establish notice identity; keep the row
        # separate and let the output flag its missing provenance.
        key = (row["notice_number"].strip().casefold(), agency or f"<missing:{index}>")
        groups.setdefault(key, []).append(row)

    def row_order(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(row.get(field, "").strip() for field in REQUIRED_FIELDS)

    resolved = []
    for group_key in sorted(groups):
        rows = groups[group_key]
        # Rows that differ only by when they were supplied are duplicate copies;
        # retaining the newest provenance avoids an unnecessary conflict.
        material_fields = tuple(field for field in REQUIRED_FIELDS if field != "received_at")
        distinct = {tuple(row.get(field, "").strip() for field in material_fields) for row in rows}
        if len(distinct) == 1:
            timestamps = [_received_at(row) for row in rows]
            known = [stamp for stamp in timestamps if stamp is not None]
            if len(known) == len(rows) and len({stamp.tzinfo is not None for stamp in known}) == 1:
                latest = max(rows, key=lambda row: _received_at(row))
            else:
                # Identical notice content can be safely collapsed; choose a
                # deterministic provenance row without comparing unlike times.
                latest = sorted(rows, key=row_order)[-1]
            resolved.append((latest, [], False))
            continue

        received = [_received_at(row) for row in rows]
        known_times = [stamp for stamp in received if stamp is not None]
        timezone_kinds = {stamp.tzinfo is not None for stamp in known_times}
        if len(known_times) != len(rows) or len(timezone_kinds) > 1:
            # Without provenance for every version, no row can be called latest.
            ordered_rows = sorted(rows, key=row_order)
            resolved.append((ordered_rows[0], ordered_rows, True))
            continue
        latest_stamp = max(known_times)
        latest_rows = [row for row, stamp in zip(rows, received) if stamp == latest_stamp]
        latest_variants = {tuple(row.get(field, "").strip() for field in material_fields) for row in latest_rows}
        if len(latest_variants) != 1:
            ordered_rows = sorted(rows, key=row_order)
            resolved.append((ordered_rows[0], ordered_rows, True))
            continue

        latest = sorted(latest_rows, key=row_order)[0]
        history = sorted((row for row in rows if row is not latest), key=row_order)
        resolved.append((latest, history, False))
    resolved.sort(key=lambda item: row_order(item[0]))
    return resolved


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
    for row, revision_history, revision_conflict in _revision_groups(notices):
        if row["county"].strip().casefold() not in normalized_counties:
            continue
        if not _matches_trade(row, trade):
            continue
        due = _date(row["bid_date"])
        if due is not None and due < cutoff:
            continue
        match = dict(row)
        match["deadline_status"] = (
            "uncertain — check controlling notice"
            if due is None
            else "uncertain - please check; verify controlling notice"
            if revision_conflict or not row["advertising_agency"].strip()
            else "upcoming — verify with issuing authority"
        )
        match["revision_history"] = [
            {
                "bid_date": prior.get("bid_date", "").strip(),
                "received_at": prior.get("received_at", "").strip(),
                "official_url": prior.get("official_url", "").strip(),
            }
            for prior in revision_history
        ]
        match["revision_conflict"] = revision_conflict
        match["revision_deadline_changed"] = any(
            prior.get("bid_date", "").strip() != row.get("bid_date", "").strip()
            for prior in revision_history
        )
        if match["revision_deadline_changed"] and not revision_conflict:
            match["deadline_status"] = "uncertain - please check; supplied revision changed the deadline"
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
        due = item["bid_date"] or "uncertain - please check (not supplied)"
        prebid = item["prebid_meeting"] or "uncertain - please check (not supplied)"
        issuer = item["advertising_agency"] or "uncertain - please check (not supplied)"
        municipality = item["municipality"] or "uncertain - please check (not supplied)"
        scope = item["description"] or "uncertain - please check (not supplied)"
        official_url = item["official_url"] or "uncertain - please check (not supplied)"
        lines.extend([
            f"## {item['project']}",
            "",
            f"- Notice: {item['notice_number']}",
            f"- Issuer: {issuer} ({municipality}, {item['county']} County)",
            f"- Bid due: {due} — {item['deadline_status']}",
            f"- Pre-bid meeting: {prebid}",
            f"- Scope notes: {scope}",
            f"- Next action: {item['next_action']}",
            f"- Official notice: {official_url}",
        ])
        if item.get("revision_conflict"):
            lines.append("- Revision conflict: uncertain - please check; supplied revisions have equal or incomplete receipt provenance.")
        for revision in item.get("revision_history", []):
            old_due = revision["bid_date"] or "uncertain - please check (not supplied)"
            lines.append(
                f"- Earlier supplied version: bid due {old_due}; received {revision['received_at'] or 'uncertain - please check'}; source {revision['official_url']}"
            )
        lines.append("")
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
