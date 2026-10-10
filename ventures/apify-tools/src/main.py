"""Apify Actor entrypoint for Mississippi contractor license lookups."""

from __future__ import annotations

import hashlib
import os

from apify import Actor

from .lookup import SOURCE_NAME, actor_queries, lookup_many


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        queries = actor_queries(actor_input)
        if not queries:
            raise ValueError("Provide a license_number, name, or one or more queries")

        for index, query in enumerate(queries):
            results = lookup_many(
                license_number=query.get("license_number") or None,
                name=query.get("name") or None,
                max_results=query.get("max_results", 1),
            )
            for result in results:
                await Actor.push_data(result)
            # Charge only after the public source answered; source outages are not billed.
            if results[0].get("verification_state") != "unverifiable" and (
                os.getenv("APIFY_IS_AT_HOME") == "1"
                or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
            ):
                search = query.get("license_number") or query.get("name")
                key = hashlib.sha256(
                    f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{index}:{search}".encode()
                ).hexdigest()
                await Actor.charge(event_name="license-lookup", count=1, idempotency_key=key)

        await Actor.set_status_message(
            f"Finished {len(queries)} lookups against {SOURCE_NAME}.",
            is_terminal=True,
        )
