"""Standalone Apify Actor adapter for the uploaded Alabama roster checker."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Callable

from scripts.verify import SourceUnavailable, actor_queries, load_roster_text, lookup_many, read_roster_file


async def run_roster_actor(
    actor: Any,
    actor_input: dict[str, Any],
    *,
    file_reader: Callable[[str], str] = read_roster_file,
    lookup: Callable[..., list[dict[str, Any]]] = lookup_many,
) -> list[dict[str, Any]]:
    queries = actor_queries(actor_input)
    roster_as_of = str(actor_input.get("roster_as_of") or "")
    source_url = str(actor_input.get("source_url") or "")
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        roster_text = file_reader(str(actor_input.get("roster_file") or ""))
        roster = load_roster_text(roster_text)
        rows = lookup(
            roster=roster,
            queries=queries,
            roster_as_of=roster_as_of,
            source_url=source_url,
            checked_at=checked_at,
        )
    except SourceUnavailable as exc:
        await actor.set_status_message(
            f"Roster file unavailable; lookup results are uncertain — please check. No lookup charge was recorded. {exc}",
            is_terminal=True,
        )
        return []

    for index, row in enumerate(rows):
        await actor.push_data(row)
        # A successful match is the only billable Alabama result. A readable
        # no-match is useful output but is deliberately free.
        if row.get("outcome") == "match" and row.get("verification_state") == "verified" and (
            os.getenv("APIFY_IS_AT_HOME") == "1"
            or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
        ):
            query = queries[index]
            search = query.get("license_number") or query.get("name") or ""
            key = hashlib.sha256(
                f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{index}:{search}".encode()
            ).hexdigest()
            await actor.charge(event_name="license-lookup", count=1, idempotency_key=key)

    await actor.set_status_message(
        f"Compared {len(rows)} lookups with the user-supplied Alabama roster snapshot.",
        is_terminal=True,
    )
    return rows
