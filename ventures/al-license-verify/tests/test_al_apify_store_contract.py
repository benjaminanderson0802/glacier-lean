from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_store_input_prefills_a_valid_fixture_lookup_without_claiming_live_board_data():
    schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text())
    assert schema["type"] == "object"
    assert schema["schemaVersion"] == 1
    assert "prefill" in schema["properties"]["queries"]
    assert schema["properties"]["queries"]["editor"] == "json"
    assert schema["properties"]["roster_file"]["editor"] == "fileupload"
    assert "live" in schema["properties"]["roster_file"]["description"].lower()


def test_store_dataset_schema_uses_apify_json_schema_fields_and_view():
    schema = json.loads((ROOT / ".actor" / "dataset_schema.json").read_text())
    assert schema["actorSpecification"] == 1
    assert schema["fields"]["type"] == "object"
    assert {"outcome", "verification_state", "source_url", "checked_at"} <= set(
        schema["fields"]["properties"]
    )
    assert schema["views"]["overview"]["display"]["component"] == "table"


def test_store_pricing_is_only_for_successful_match_rows_after_dataset_write(monkeypatch):
    spec = importlib.util.spec_from_file_location("al_actor_template", ROOT / "src" / "actor_template.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_roster_actor = module.run_roster_actor

    class FakeActor:
        def __init__(self):
            self.rows = []
            self.charges = []

        async def push_data(self, row):
            self.rows.append(row)

        async def charge(self, **kwargs):
            assert self.rows, "billing must follow a successful dataset write"
            self.charges.append(kwargs)

        async def set_status_message(self, *args, **kwargs):
            pass

    fixture_csv = (ROOT / "tests" / "fixtures" / "alabama_roster.csv").read_text()
    schema = json.loads((ROOT / ".actor" / "input_schema.json").read_text())
    prefilled = schema["properties"]["queries"]["prefill"]

    def read_file(_):
        return fixture_csv

    async def run(state):
        actor = FakeActor()
        actor_input = {
            "roster_file": "apify-file",
            "roster_as_of": schema["properties"]["roster_as_of"]["prefill"],
            "source_url": schema["properties"]["source_url"]["prefill"],
            "queries": prefilled if state == "verified" else [{"license_number": "AL-MISSING-9999"}],
        }
        if state == "uncertain":
            actor_input["roster_as_of"] = "2020-01-01"
        await run_roster_actor(
            actor,
            actor_input,
            file_reader=read_file,
        )
        return actor

    import asyncio
    monkeypatch.setenv("ACTOR_TEST_PAY_PER_EVENT", "true")

    success = asyncio.run(run("verified"))
    no_match = asyncio.run(run("no_match"))
    uncertain = asyncio.run(run("uncertain"))
    assert len(success.rows) == 1 and len(success.charges) == 1
    assert success.charges[0]["event_name"] == "license-lookup"
    assert no_match.rows and no_match.charges == []
    assert uncertain.rows and uncertain.charges == []


@pytest.mark.parametrize("folder", ["listing"])
def test_alabama_listing_has_console_fields_privacy_and_owner_steps(folder):
    listing = ROOT / folder
    required = {"FIELDS.md", "PRICING.md", "PRIVACY.md", "OWNER-STEPS.md", "README.md", "sample-output.json", "logo.png"}
    assert required <= {path.name for path in listing.iterdir()}
