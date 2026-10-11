"""Apify lifecycle, dataset output and per-query event billing."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any


async def run_actor_queries(actor: Any, queries: Sequence[Mapping[str, Any]], *, check_one: Callable[[Mapping[str, Any]], dict[str, Any]]) -> None:
    for index, query in enumerate(queries):
        result = check_one(query)
        await actor.push_data(result)
        sources = result.get("sources_checked", {})
        source_errors = [source for source in sources.values() if source.get("status") == "error"]
        source_ok = any(source.get("status") == "ok" for source in sources.values())
        outage_only = bool(source_errors) and not source_ok
        if not outage_only and (
            os.getenv("APIFY_IS_AT_HOME") == "1"
            or os.getenv("ACTOR_TEST_PAY_PER_EVENT", "").lower() == "true"
        ):
            item_id = ",".join(str(query.get(key, "")) for key in ("barcode", "brand", "model", "product_name", "year"))
            key = hashlib.sha256(f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{index}:{item_id}".encode()).hexdigest()
            await actor.charge(event_name="recall-check", count=1, idempotency_key=key)
    await actor.set_status_message(f"Finished {len(queries)} product recall checks.", is_terminal=True)
