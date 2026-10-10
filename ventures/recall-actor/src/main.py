"""Apify Actor entrypoint."""

from __future__ import annotations

from apify import Actor

from .actor_template import run_actor_queries
from .checker import check_one
from .inputs import normalize_input


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        queries = normalize_input(actor_input)
        await run_actor_queries(Actor, queries, check_one=check_one)
