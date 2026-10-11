#!/usr/bin/env python3
"""Compare two saved SAM.gov Opportunities API v2 snapshots and render a digest."""

from __future__ import annotations

import argparse
import json
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
COVERAGE_NOTE = (
    "Changes are observed only between these saved snapshots; this does not reconstruct "
    "amendments published before the first snapshot. Verify each notice on SAM.gov."
)


def _records(snapshot: dict[str, Any], naics_codes: set[str]) -> dict[str, dict[str, Any]]:
    data = snapshot.get("opportunitiesData")
    if not isinstance(data, list):
        raise ValueError("Snapshot must contain an opportunitiesData list from the v2 response.")
    records = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        notice_id = str(row.get("noticeId", "")).strip()
        naics = str(row.get("naicsCode") or row.get("naics") or "").strip()
        if notice_id and naics in naics_codes:
            records[notice_id] = row
    return records


def _notice_url(record: dict[str, Any]) -> str:
    for link in record.get("links", []):
        if isinstance(link, dict) and link.get("href"):
            return str(link["href"])
    return "https://sam.gov/opportunities"


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

    old = _records(before, naics_codes)
    new = _records(after, naics_codes)
    events: list[dict[str, Any]] = []
    for notice_id, current in new.items():
        previous = old.get(notice_id)
        naics = str(current.get("naicsCode") or current.get("naics") or "").strip()
        if previous is None:
            events.append(
                {
                    "kind": "new_notice",
                    "notice_id": notice_id,
                    "title": current.get("title", "Untitled SAM.gov notice"),
                    "solicitation_number": current.get("solicitationNumber", ""),
                    "naics_code": naics,
                    "response_deadline": current.get("responseDeadLine", ""),
                    "amendment": _amendment_value(current),
                    "source_url": _notice_url(current),
                }
            )
            continue

        old_deadline = str(previous.get("responseDeadLine") or "")
        current_deadline = str(current.get("responseDeadLine") or "")
        old_amendment = _amendment_value(previous)
        current_amendment = _amendment_value(current)
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
    retrieved_at = str(after.get("retrieved_at", ""))
    snapshot_date = retrieved_at[:10] if len(retrieved_at) >= 10 else "unknown date"
    selected_codes = sorted(naics_codes)
    trade = NAICS_NAMES.get(selected_codes[0], f"NAICS {selected_codes[0]}")
    source_url = str(after.get("source_url") or before.get("source_url") or SAM_SEARCH_URL)
    return {
        "status": "match" if events else f"no match found in SAM.gov as of {snapshot_date}",
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
