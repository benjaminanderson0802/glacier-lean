"""Apify Actor entrypoint for Louisiana contractor license lookups."""

from __future__ import annotations

from apify import Actor

from .actor_template import run_lookup_actor
from .lookup import SOURCE_NAME, actor_queries, lookup_many


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        queries = actor_queries(actor_input)
        if not queries:
            raise ValueError("Provide a license_number, name, or one or more queries")
        await run_lookup_actor(
            Actor,
            queries,
            lookup_many=lookup_many,
            source_name=SOURCE_NAME,
            event_name="license-lookup",
        )
