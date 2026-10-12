from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_store_input_prefills_watch_and_marks_sam_api_key_as_secret():
    schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text())
    assert schema["schemaVersion"] == 1
    assert schema["properties"]["naics_codes"]["prefill"] == ["423840"]
    assert schema["properties"]["api_key"]["isSecret"] is True
    assert schema["properties"]["api_key"]["editor"] == "textfield"
    assert "stored encrypted" in schema["properties"]["api_key"]["description"].lower()


def test_store_dataset_schema_uses_apify_json_schema_fields_and_view():
    schema = json.loads((ROOT / ".actor" / "dataset_schema.json").read_text())
    assert schema["actorSpecification"] == 1
    assert schema["fields"]["type"] == "object"
    assert {"outcome", "verification_state", "event_kind", "notice_id", "source_url"} <= set(
        schema["fields"]["properties"]
    )
    assert schema["views"]["overview"]["display"]["component"] == "table"


def test_actor_saves_first_baseline_without_charge_then_charges_only_written_change_rows(monkeypatch):
    spec = importlib.util.spec_from_file_location("sam_actor_template", ROOT / "src" / "actor_template.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_sam_actor = module.run_sam_actor

    class FakeStore:
        def __init__(self):
            self.values = {}

        async def get_value(self, key):
            return self.values.get(key)

        async def set_value(self, key, value, **kwargs):
            self.values[key] = value

    class FakeActor:
        def __init__(self):
            self.rows = []
            self.charges = []
            self.status = None

        async def push_data(self, row):
            self.rows.append(row)

        async def charge(self, **kwargs):
            assert self.rows, "billing must follow a successful dataset write"
            self.charges.append(kwargs)

        async def set_status_message(self, message, **kwargs):
            self.status = message

    snapshot = {"opportunitiesData": [{"noticeId": "N-1"}]}
    event = {"kind": "deadline_change", "notice_id": "N-1", "source_url": "https://sam.gov/opp/N-1/view"}
    store = FakeStore()
    actor = FakeActor()
    monkeypatch.setenv("ACTOR_TEST_PAY_PER_EVENT", "true")
    schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text())
    actor_input = {"api_key": "test-secret", "naics_codes": schema["properties"]["naics_codes"]["prefill"]}

    def first_collect(**kwargs):
        return snapshot

    asyncio = __import__("asyncio")
    asyncio.run(run_sam_actor(
        actor, actor_input,
        store=store, collect=first_collect,
        digest=lambda before, after, naics_codes: {"events": [], "status": "baseline"},
    ))
    assert actor.charges == []
    assert actor.rows[0]["verification_state"] == "uncertain"
    assert store.values
    assert "test-secret" not in repr(actor.rows + list(store.values.values()))

    actor = FakeActor()

    def next_collect(**kwargs):
        return {"opportunitiesData": [{"noticeId": "N-1", "responseDeadLine": "2026-11-01"}]}

    asyncio.run(run_sam_actor(
        actor, actor_input,
        store=store, collect=next_collect,
        digest=lambda before, after, naics_codes: {"events": [event], "status": "match", "snapshot_date": "2026-10-11", "source_url": "https://api.sam.gov/opportunities/v2/search", "retrieved_at": "2026-10-11T12:00:00Z"},
    ))
    assert len(actor.rows) == 1
    assert len(actor.charges) == 1
    assert actor.charges[0]["event_name"] == "opportunity-change"


@pytest.mark.parametrize("state", ["uncertain", "no_match", "outage"])
def test_actor_does_not_charge_uncertain_no_match_or_outage_rows(state):
    spec = importlib.util.spec_from_file_location("sam_actor_template", ROOT / "src" / "actor_template.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_sam_actor = module.run_sam_actor

    class FakeStore:
        async def get_value(self, key):
            return {"opportunitiesData": [], "prior": True}

        async def set_value(self, key, value, **kwargs):
            pass

    class FakeActor:
        def __init__(self):
            self.rows = []
            self.charges = []

        async def push_data(self, row):
            self.rows.append(row)

        async def charge(self, **kwargs):
            self.charges.append(kwargs)

        async def set_status_message(self, *args, **kwargs):
            pass

    def collect(**kwargs):
        if state == "outage":
            raise RuntimeError("source unavailable")
        return {"opportunitiesData": []}

    status = {"uncertain": "uncertain — please check", "no_match": "no match found in SAM.gov as of 2026-10-11"}
    def digest(*args, **kwargs):
        return {"events": [], "status": status[state], "snapshot_date": "2026-10-11", "retrieved_at": "2026-10-11T12:00:00Z", "source_url": "https://api.sam.gov/opportunities/v2/search"}

    import asyncio
    actor = FakeActor()
    asyncio.run(run_sam_actor(actor, {"api_key": "key", "naics_codes": ["423840"]}, store=FakeStore(), collect=collect, digest=digest))
    assert actor.rows
    assert actor.charges == []


def test_sam_listing_has_console_fields_privacy_and_owner_steps():
    listing = ROOT / "listing"
    required = {"FIELDS.md", "PRICING.md", "PRIVACY.md", "OWNER-STEPS.md", "README.md", "sample-output.json", "logo.png"}
    assert required <= {path.name for path in listing.iterdir()}
