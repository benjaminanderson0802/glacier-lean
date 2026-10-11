"""Run the Alabama roster verification Actor."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from apify import Actor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify import actor_queries, load_roster_text, lookup_many, read_roster_file  # noqa: E402


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        queries = actor_queries(actor_input)
        roster_text = read_roster_file(str(actor_input.get("roster_file") or ""))
        roster = load_roster_text(roster_text)
        results = lookup_many(
            roster=roster,
            queries=queries,
            roster_as_of=str(actor_input.get("roster_as_of") or ""),
            source_url=str(actor_input.get("source_url") or ""),
            checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        for index, result in enumerate(results):
            await Actor.push_data(result)
            if result["verification_state"] != "unverifiable" and (
                os.getenv("APIFY_IS_AT_HOME") == "1"
                or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
            ):
                import hashlib

                search = queries[index].get("license_number") or queries[index].get("name")
                key = hashlib.sha256(
                    f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{index}:{search}".encode()
                ).hexdigest()
                await Actor.charge(event_name="license-lookup", count=1, idempotency_key=key)
        await Actor.set_status_message(
            f"Compared {len(results)} queries with the user-supplied Alabama roster snapshot.",
            is_terminal=True,
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
