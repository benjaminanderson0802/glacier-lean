"""Reusable Apify runner for a source-specific public-data lookup adapter."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any


async def run_lookup_actor(
    actor: Any,
    queries: Sequence[Mapping[str, Any]],
    *,
    lookup_many: Callable[..., list[dict[str, object]]],
    source_name: str,
    event_name: str,
) -> None:
    """Run normalized lookup inputs, publish records, and charge readable results.

    A board adapter owns input normalization and public-source parsing. This
    template owns the shared Actor lifecycle, output push, idempotent event
    charge, and terminal status behavior.
    """
    for index, query in enumerate(queries):
        results = lookup_many(
            license_number=query.get("license_number") or None,
            name=query.get("name") or None,
            max_results=query.get("max_results", 1),
        )
        for result in results:
            await actor.push_data(result)
        if results and results[0].get("verification_state") != "unverifiable" and (
            os.getenv("APIFY_IS_AT_HOME") == "1"
            or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
        ):
            search = query.get("license_number") or query.get("name")
            key = hashlib.sha256(
                f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{index}:{search}".encode()
            ).hexdigest()
            await actor.charge(event_name=event_name, count=1, idempotency_key=key)

    await actor.set_status_message(
        f"Finished {len(queries)} lookups against {source_name}.",
        is_terminal=True,
    )
