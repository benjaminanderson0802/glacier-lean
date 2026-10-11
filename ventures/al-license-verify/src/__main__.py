"""Run the Alabama roster verification Actor."""

from __future__ import annotations

import sys
from pathlib import Path
from scripts.verify import lookup_many, read_roster_file  # noqa: E402

from apify import Actor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.actor_template import run_roster_actor  # noqa: E402


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        await run_roster_actor(
            Actor,
            actor_input,
            file_reader=read_roster_file,
            lookup=lookup_many,
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
