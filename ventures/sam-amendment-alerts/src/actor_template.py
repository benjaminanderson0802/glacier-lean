"""Standalone Apify Actor adapter for dated SAM.gov opportunity change alerts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_support_module(module_name: str, file_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "scripts" / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Actor support module {file_name}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


collect_snapshot = _load_support_module("sam_actor_collect_snapshot", "collect_snapshot.py").collect_snapshot
build_digest = _load_support_module("sam_actor_digest", "digest.py").build_digest


SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
STATE_KEY_PREFIX = "SAM-SNAPSHOT-"


def _state_key(naics_codes: list[str]) -> str:
    scope = ",".join(sorted(set(naics_codes)))
    return STATE_KEY_PREFIX + hashlib.sha256(scope.encode("ascii")).hexdigest()[:24]


def _uncertain_row(message: str, *, source_url: str = SAM_SEARCH_URL) -> dict[str, Any]:
    # Error details are intentionally not copied from HTTP exceptions: the API
    # key is a query parameter on SAM requests and must never reach output.
    return {
        "outcome": "uncertain — please check",
        "verification_state": "unverifiable",
        "event_kind": "uncertain",
        "notice_id": "",
        "solicitation_number": "",
        "title": "",
        "naics_code": "",
        "previous_deadline": "",
        "response_deadline": "",
        "previous_amendment": "",
        "amendment": "",
        "source_url": source_url,
        "checked_at": "",
        "limitations": message,
    }


async def run_sam_actor(
    actor: Any,
    actor_input: dict[str, Any],
    *,
    store: Any,
    collect: Callable[..., dict[str, Any]] = collect_snapshot,
    digest: Callable[..., dict[str, Any]] = build_digest,
) -> list[dict[str, Any]]:
    codes_value = actor_input.get("naics_codes") or ["423840"]
    if not isinstance(codes_value, list) or not codes_value:
        raise ValueError("Enter at least one NAICS code.")
    codes = sorted({str(code).strip() for code in codes_value})
    if any(not code.isdigit() or not 2 <= len(code) <= 6 for code in codes):
        raise ValueError("Each NAICS code must contain 2 to 6 digits.")
    api_key = actor_input.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        rows = [_uncertain_row("Enter your SAM.gov API key in the encrypted secret field.")]
        await actor.push_data(rows[0])
        await actor.set_status_message("SAM.gov key is missing; no event was charged.", is_terminal=True)
        return rows

    state_key = _state_key(codes)
    previous = await store.get_value(state_key)
    try:
        current = collect(naics_codes=codes, api_key=api_key.strip())
        if not isinstance(current, dict) or current.get("complete") is False or not isinstance(current.get("opportunitiesData"), list):
            raise ValueError("SAM.gov did not return a complete opportunity snapshot.")
    except Exception:
        rows = [_uncertain_row("SAM.gov was unavailable or returned incomplete data. No change event was charged.")]
        await actor.push_data(rows[0])
        await actor.set_status_message("SAM.gov comparison was uncertain; no change event was charged.", is_terminal=True)
        return rows

    if previous is None:
        rows = [{
            **_uncertain_row(
                "This first complete snapshot is the baseline. A later successful run can report changes observed after this date; earlier amendments are not reconstructed."
            ),
            "verification_state": "uncertain",
            "event_kind": "baseline_saved",
            "title": "Initial SAM.gov baseline saved",
            "naics_code": ",".join(codes),
            "checked_at": str(current.get("retrieved_at") or ""),
            "limitations": "This first complete snapshot is the baseline. A later successful run can report changes observed after this date; earlier amendments are not reconstructed.",
        }]
        await actor.push_data(rows[0])
        await store.set_value(state_key, current, content_type="application/json")
        await actor.set_status_message("Initial SAM.gov baseline saved; no change event was charged.", is_terminal=True)
        return rows

    try:
        report = digest(previous, current, naics_codes=set(codes))
        checked_at = str(report.get("retrieved_at") or current.get("retrieved_at") or "")
        report_url = str(report.get("source_url") or SAM_SEARCH_URL)
        events = report.get("events")
        if not isinstance(events, list):
            raise ValueError("SAM.gov comparison returned an invalid event list.")
        if report.get("status") in {"uncertain - please check", "uncertain — please check"}:
            rows = [_uncertain_row("One or more records lacked enough dated information for a reliable comparison.", source_url=report_url)]
        elif not events:
            rows = [{
                **_uncertain_row(
                    "No new notice, version, or response-deadline change was found between these complete snapshots.",
                    source_url=report_url,
                ),
                "outcome": f"no change found in SAM.gov as of {report.get('snapshot_date') or checked_at[:10]}",
                "verification_state": "verified",
                "event_kind": "no_change",
                "naics_code": ",".join(codes),
                "checked_at": checked_at,
            }]
        else:
            rows = []
            for event in events:
                if not isinstance(event, dict):
                    raise ValueError("SAM.gov comparison returned a malformed change event.")
                is_uncertain = bool(event.get("uncertain")) or event.get("kind") == "uncertain"
                rows.append({
                    "outcome": "uncertain — please check" if is_uncertain else "match",
                    "verification_state": "uncertain" if is_uncertain else "verified",
                    "event_kind": str(event.get("kind") or "uncertain"),
                    "notice_id": str(event.get("notice_id") or ""),
                    "solicitation_number": str(event.get("solicitation_number") or ""),
                    "title": str(event.get("title") or ""),
                    "naics_code": str(event.get("naics_code") or ""),
                    "previous_deadline": str(event.get("previous_deadline") or ""),
                    "response_deadline": str(event.get("response_deadline") or ""),
                    "previous_amendment": str(event.get("previous_amendment") or ""),
                    "amendment": str(event.get("amendment") or ""),
                    "source_url": str(event.get("source_url") or report_url),
                    "checked_at": checked_at,
                    "limitations": "Observed between the saved snapshots only. Verify the current notice and response deadline on SAM.gov.",
                })
    except Exception:
        rows = [_uncertain_row("The snapshots could not be compared reliably. No change event was charged.")]
        await actor.push_data(rows[0])
        await actor.set_status_message("SAM.gov comparison was uncertain; no change event was charged.", is_terminal=True)
        return rows

    for row in rows:
        await actor.push_data(row)
        if row["verification_state"] == "verified" and row["event_kind"] not in {"no_change", "baseline_saved"} and (
            os.getenv("APIFY_IS_AT_HOME") == "1"
            or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
        ):
            fingerprint = json.dumps(
                {
                    field: row[field]
                    for field in (
                        "event_kind", "notice_id", "solicitation_number", "naics_code",
                        "previous_deadline", "response_deadline", "previous_amendment", "amendment",
                    )
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            idempotency_key = hashlib.sha256(f"{state_key}:{fingerprint}".encode()).hexdigest()
            await actor.charge(event_name="opportunity-change", count=1, idempotency_key=idempotency_key)

    # Advance only after every output row and event charge succeeds. Failed
    # writes leave the prior snapshot available for a safe retry.
    if all(row["verification_state"] == "verified" for row in rows):
        await store.set_value(state_key, current, content_type="application/json")
    await actor.set_status_message(f"Compared SAM.gov snapshots and wrote {len(rows)} result rows.", is_terminal=True)
    return rows
