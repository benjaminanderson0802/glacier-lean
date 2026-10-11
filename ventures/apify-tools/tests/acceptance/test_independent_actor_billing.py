"""Independent local checks for the Mississippi Actor's billing boundary."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import patch
from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.actor_template import run_lookup_actor


def test_dataset_output_schema_declares_every_emitted_column() -> None:
    schema = json.loads((ROOT / ".actor" / "dataset_schema.json").read_text(encoding="utf-8"))
    fields = schema["fields"]
    displayed = schema["views"]["overview"]["transformation"]["fields"]
    assert {"outcome", "verification_state", "license_number", "status", "expiration_date", "source_url", "checked_at"} <= fields.keys()
    assert set(displayed) <= fields.keys()


class FakeActor:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []
        self.charges: list[dict[str, object]] = []
        self.status: tuple[str, bool] | None = None

    async def push_data(self, row: dict[str, object]) -> None:
        self.rows.append(row)

    async def charge(self, **kwargs: object) -> None:
        self.charges.append(kwargs)

    async def set_status_message(self, message: str, *, is_terminal: bool) -> None:
        self.status = (message, is_terminal)


def run(result: dict[str, object], *, enabled: bool) -> FakeActor:
    actor = FakeActor()
    environment = {"APIFY_ACTOR_RUN_ID": "independent-local-test"}
    if enabled:
        environment["ACTOR_TEST_PAY_PER_EVENT"] = "true"
    with patch.dict("os.environ", environment, clear=True):
        asyncio.run(run_lookup_actor(
            actor,
            [{"license_number": "22649", "name": None, "max_results": 1}],
            lookup_many=lambda **_: [result],
            source_name="Mississippi test fixture",
            event_name="license-lookup",
        ))
    return actor


@pytest.mark.parametrize("state", ["verified"])
def test_successful_readable_lookup_emits_one_configured_event(state: str) -> None:
    row = {"outcome": "match", "verification_state": state, "status": "Licensed"}
    actor = run(row, enabled=True)
    assert actor.rows == [row]
    assert len(actor.charges) == 1
    assert actor.charges[0]["event_name"] == "license-lookup"
    assert actor.status == ("Finished 1 lookups against Mississippi test fixture.", True)


def test_verified_readable_no_match_emits_one_configured_event() -> None:
    row = {"outcome": "no match found in Mississippi as of 2026-10-11", "verification_state": "verified"}
    assert len(run(row, enabled=True).charges) == 1


@pytest.mark.parametrize("state", ["uncertain", "unverifiable"])
def test_uncertain_or_unverifiable_lookup_does_not_emit_billable_event(state: str) -> None:
    row = {"outcome": "uncertain — please check", "verification_state": state}
    actor = run(row, enabled=True)
    assert actor.rows == [row]
    assert actor.charges == []


def test_local_sdk_default_does_not_emit_billable_event() -> None:
    row = {"outcome": "match", "verification_state": "verified"}
    assert run(row, enabled=False).charges == []
