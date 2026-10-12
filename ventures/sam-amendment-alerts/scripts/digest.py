#!/usr/bin/env python3
"""Compare two saved SAM.gov Opportunities API v2 snapshots and render a digest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


NAICS_NAMES = {
    "423840": "industrial supplies merchant wholesalers",
    "423830": "industrial machinery and equipment merchant wholesalers",
    "423710": "hardware merchant wholesalers",
    "423610": "electrical apparatus and equipment wholesalers",
    "423120": "motor vehicle supplies and new parts merchant wholesalers",
}
SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
UNCERTAIN = "uncertain - please check"
COVERAGE_NOTE = (
    "Changes are observed only between these saved snapshots; this does not reconstruct "
    "amendments published before the first snapshot. Verify each notice on SAM.gov."
)


def _records(snapshot: dict[str, Any], naics_codes: set[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be an object from the v2 response with local capture metadata.")
    if snapshot.get("error"):
        raise ValueError("SAM.gov snapshot contains an error response, not opportunity data.")
    data = snapshot.get("opportunitiesData")
    if not isinstance(data, list):
        raise ValueError("Snapshot must contain an opportunitiesData list from the v2 response.")
    records: dict[str, dict[str, Any]] = {}
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("Snapshot contains a malformed opportunity row.")
        notice_id = row.get("noticeId")
        naics = row.get("naicsCode")
        if not isinstance(notice_id, str) or not notice_id.strip():
            raise ValueError("Snapshot opportunity row is missing its documented noticeId.")
        if not isinstance(naics, str) or not naics.strip():
            raise ValueError(f"Notice {notice_id.strip()} is missing its documented naicsCode.")
        notice_id = notice_id.strip()
        naics = naics.strip()
        if "title" in row and not isinstance(row["title"], str):
            raise ValueError(f"Notice {notice_id} has a malformed title.")
        if "responseDeadLine" in row and not isinstance(row["responseDeadLine"], str):
            raise ValueError(f"Notice {notice_id} has a malformed responseDeadLine.")
        if "uiLink" in row and not isinstance(row["uiLink"], str):
            raise ValueError(f"Notice {notice_id} has a malformed uiLink.")
        if "links" in row and (
            not isinstance(row["links"], list)
            or any(not isinstance(link, dict) for link in row["links"])
            or any(not isinstance(link.get("href"), str) for link in row["links"])
        ):
            raise ValueError(f"Notice {notice_id} has malformed links.")
        if naics not in naics_codes:
            continue
        previous = records.get(notice_id)
        if previous is not None and previous != row:
            raise ValueError(f"Snapshot contains conflicting duplicate rows for noticeId {notice_id}.")
        records[notice_id] = row
    return records


def _notice_url(record: dict[str, Any]) -> str:
    ui_link = record.get("uiLink")
    if isinstance(ui_link, str) and ui_link.startswith("https://sam.gov/"):
        return ui_link
    links = record.get("links", [])
    if not isinstance(links, list):
        raise ValueError(f"Notice {record.get('noticeId', '')} has malformed links.")
    for link in links:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        if (isinstance(href, str) and href.startswith("https://sam.gov/")
                and str(record.get("noticeId", "")) in href):
            return href
    # The API self link may require a key. Build a notice-specific public UI link
    # from the documented identifier instead of linking customers back to the API.
    notice_id = str(record.get("noticeId", "")).strip()
    if notice_id:
        return f"https://sam.gov/opp/{notice_id}/view"
    raise ValueError("Notice is missing a usable notice-specific SAM.gov link.")


def _retrieval_time(snapshot: dict[str, Any], name: str) -> datetime:
    value = snapshot.get("retrieved_at")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} snapshot is missing local retrieved_at metadata.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} snapshot has malformed retrieved_at metadata.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} snapshot retrieved_at must include a timezone.")
    return parsed


def _validate_scope_and_coverage(snapshot: dict[str, Any], naics_codes: set[str], name: str) -> None:
    """Check local query scope and that the saved rows cover the v2 result count."""
    source_url = snapshot.get("source_url")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError(f"{name} snapshot is missing local source_url metadata.")
    for key in ("naics_codes", "selected_naics_codes"):
        if key in snapshot:
            recorded = snapshot[key]
            if not isinstance(recorded, (list, tuple, set)) or {str(code) for code in recorded} != naics_codes:
                raise ValueError(f"{name} snapshot NAICS scope does not match the requested comparison scope.")
            break

    total = snapshot.get("totalRecords")
    limit = snapshot.get("limit")
    offset = snapshot.get("offset")
    if (isinstance(total, bool) or not isinstance(total, int) or total < 0
            or isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
            or isinstance(offset, bool) or not isinstance(offset, int) or offset < 0):
        raise ValueError(f"{name} snapshot is missing valid v2 pagination metadata.")

    matching_rows = [
        row for row in snapshot["opportunitiesData"]
        if isinstance(row, dict) and isinstance(row.get("naicsCode"), str)
        and row["naicsCode"].strip() in naics_codes
    ]
    # A plain saved envelope describes one page. Multi-page captures must record
    # their contiguous page offsets/counts so a short or capped capture is not
    # mistaken for a complete negative result.
    pages = snapshot.get("page_coverage")
    if pages is None:
        complete = offset == 0 and total <= limit and len(matching_rows) == total
    else:
        if not isinstance(pages, list):
            raise ValueError(f"{name} snapshot page_coverage must be a list.")
        if any(not isinstance(page, dict) for page in pages):
            raise ValueError(f"{name} snapshot has malformed page_coverage entries.")
        coverage = [(page.get("offset"), page.get("count")) for page in pages]
        if any(
            isinstance(page_offset, bool) or not isinstance(page_offset, int)
            or isinstance(page_count, bool) or not isinstance(page_count, int)
            for page_offset, page_count in coverage
        ):
            raise ValueError(f"{name} snapshot has malformed page_coverage offsets or counts.")
        coverage.sort(key=lambda page: page[0])
        cursor = 0
        valid_pages = True
        for page_offset, page_count in coverage:
            if page_offset != cursor or page_count <= 0:
                valid_pages = False
                break
            cursor += page_count
        complete = valid_pages and cursor == total and len(matching_rows) == total
    if not complete:
        raise ValueError(f"{name} snapshot is incomplete; page coverage does not account for totalRecords.")


def _amendment_value(record: dict[str, Any]) -> str:
    for key in ("amendmentNumber", "version"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def build_digest(
    before: dict[str, Any], after: dict[str, Any], *, naics_codes: set[str]
) -> dict[str, Any]:
    """Return factual differences observed between two v2 snapshots."""
    if not naics_codes:
        raise ValueError("At least one NAICS code is required.")

    before_time = _retrieval_time(before, "Earlier")
    after_time = _retrieval_time(after, "Later")
    if before_time > after_time:
        raise ValueError("Snapshots must be dated in chronological order; the earlier snapshot is later than the newer one.")
    old = _records(before, naics_codes)
    new = _records(after, naics_codes)
    _validate_scope_and_coverage(before, naics_codes, "Earlier")
    _validate_scope_and_coverage(after, naics_codes, "Later")
    if before["source_url"].strip() != after["source_url"].strip():
        raise ValueError("Snapshots were captured from different source URLs and cannot be compared.")
    events: list[dict[str, Any]] = []
    has_missing_deadline = False
    for notice_id, current in new.items():
        previous = old.get(notice_id)
        naics = str(current.get("naicsCode") or current.get("naics") or "").strip()
        current_deadline = current.get("responseDeadLine")
        if not isinstance(current_deadline, str) or not current_deadline.strip():
            current_deadline = ""
            has_missing_deadline = True
        if previous is None:
            events.append(
                {
                    "kind": "new_notice",
                    "notice_id": notice_id,
                    "title": current.get("title", "Untitled SAM.gov notice"),
                    "solicitation_number": current.get("solicitationNumber", ""),
                    "naics_code": naics,
                    "response_deadline": current_deadline or UNCERTAIN,
                    "uncertain": not bool(current_deadline),
                    "amendment": _amendment_value(current),
                    "source_url": _notice_url(current),
                }
            )
            continue

        old_deadline_raw = previous.get("responseDeadLine")
        old_deadline = old_deadline_raw.strip() if isinstance(old_deadline_raw, str) else ""
        if not old_deadline:
            has_missing_deadline = True
        old_amendment = _amendment_value(previous)
        current_amendment = _amendment_value(current)
        if not old_deadline or not current_deadline:
            events.append(
                {
                    "kind": "uncertain",
                    "notice_id": notice_id,
                    "title": current.get("title", "Untitled SAM.gov notice"),
                    "solicitation_number": current.get("solicitationNumber", ""),
                    "naics_code": naics,
                    "previous_deadline": old_deadline or UNCERTAIN,
                    "response_deadline": current_deadline or UNCERTAIN,
                    "previous_amendment": old_amendment,
                    "amendment": current_amendment,
                    "source_url": _notice_url(current),
                    "uncertain": True,
                }
            )
            continue
        deadline_changed = old_deadline != current_deadline
        amendment_changed = bool(current_amendment and old_amendment != current_amendment)
        if not deadline_changed and not amendment_changed:
            continue
        if deadline_changed and amendment_changed:
            kind = "amendment_and_deadline_change"
        elif deadline_changed:
            kind = "deadline_change"
        else:
            kind = "amendment"
        events.append(
            {
                "kind": kind,
                "notice_id": notice_id,
                "title": current.get("title", "Untitled SAM.gov notice"),
                "solicitation_number": current.get("solicitationNumber", ""),
                "naics_code": naics,
                "previous_deadline": old_deadline,
                "response_deadline": current_deadline,
                "previous_amendment": old_amendment,
                "amendment": current_amendment,
                "modified_date": current.get("modifiedDate", ""),
                "source_url": _notice_url(current),
            }
        )

    events.sort(key=lambda event: (event["kind"] != "deadline_change", event["response_deadline"], event["notice_id"]))
    retrieved_at = str(after["retrieved_at"])
    snapshot_date = retrieved_at[:10]
    selected_codes = sorted(naics_codes)
    trade = NAICS_NAMES.get(selected_codes[0], f"NAICS {selected_codes[0]}")
    source_url = str(after.get("source_url") or before.get("source_url") or SAM_SEARCH_URL)
    return {
        "status": UNCERTAIN if has_missing_deadline else ("match" if events else f"no match found in SAM.gov as of {snapshot_date}"),
        "trade": trade,
        "naics_codes": selected_codes,
        "snapshot_date": snapshot_date,
        "retrieved_at": retrieved_at,
        "source_url": source_url,
        "coverage_note": COVERAGE_NOTE,
        "events": events,
    }


def render_markdown(digest: dict[str, Any]) -> str:
    lines = [
        f"# SAM opportunity change digest — {digest['snapshot_date']}",
        "",
        f"**Result:** {digest['status']}",
        f"**Trade watched:** {digest['trade']} ({', '.join(digest['naics_codes'])})",
        f"**Retrieved:** {digest['retrieved_at'] or 'not recorded'}",
        f"**Source:** {digest['source_url']}",
        "",
    ]
    if digest["events"]:
        for event in digest["events"]:
            lines.extend(
                [
                    f"## {event['kind'].replace('_', ' ')} — {event['solicitation_number'] or event['notice_id']}",
                    "",
                    f"- Notice: {event['title']}",
                    f"- Response deadline: {event.get('previous_deadline') or 'not present in prior snapshot'} → {event['response_deadline'] or 'not listed'}",
                    f"- Amendment/version: {event.get('previous_amendment') or 'not recorded'} → {event.get('amendment') or 'not recorded'}",
                    f"- NAICS: {event['naics_code']}",
                    f"- Official notice: {event['source_url']}",
                    "",
                ]
            )
    else:
        lines.extend(["No new notice, version, or response-deadline change was found in these snapshots.", ""])
    lines.extend([f"**Coverage:** {digest['coverage_note']}", ""])
    return "\n".join(lines)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path, help="earlier saved API snapshot JSON")
    parser.add_argument("--after", required=True, type=Path, help="later saved API snapshot JSON")
    parser.add_argument("--naics", action="append", required=True, help="NAICS code to include; repeat as needed")
    parser.add_argument("--output", required=True, type=Path, help="write the dated Markdown digest here")
    args = parser.parse_args()
    digest = build_digest(_load(args.before), _load(args.after), naics_codes=set(args.naics))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(digest), encoding="utf-8")
    print(f"{digest['status']} — wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
