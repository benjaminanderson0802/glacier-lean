"""Run the SAM.gov change-alert Actor."""

from __future__ import annotations

import sys
from pathlib import Path

from apify import Actor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.actor_template import run_sam_actor  # noqa: E402


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        store = await Actor.open_key_value_store(name="sam-amendment-alerts-state")
        await run_sam_actor(Actor, actor_input, store=store)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
