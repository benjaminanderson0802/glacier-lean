"""Independent PH12 recall-source and Actor-output acceptance checks."""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_openfda_not_found_is_a_valid_empty_response(monkeypatch):
    from src import sources

    payload = json.loads((Path(__file__).parent / "fixtures/openfda-not-found.json").read_text(encoding="utf-8"))

    class Response:
        status_code = 404
        def json(self): return payload
        def raise_for_status(self): raise AssertionError("NOT_FOUND is an expected empty search")

    monkeypatch.setattr(sources, "_polite_wait", lambda: None)
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: Response())
    assert sources.request_json("https://api.fda.gov/device/enforcement.json", {"search": "x"}) == {
        "results": [], "meta": {"no_records": True}
    }


def test_cpsc_uses_bounded_phrase_queries_and_deduplicates_results(monkeypatch):
    from src import sources

    calls = []
    record = {"RecallNumber": "18-101", "Title": "Rock 'n Play Sleeper", "URL": "https://www.cpsc.gov/Recalls/2019/Example"}
    def fake_request(url, params):
        calls.append(dict(params))
        if params.get("ProductName") == "Rock 'n Play" or params.get("RecallTitle") == "Rock 'n Play":
            return [record]
        return []
    monkeypatch.setattr(sources, "request_json", fake_request)
    matches, statuses = sources.check_sources({"brand": "Fisher-Price", "product_name": "Rock 'n Play Sleeper"})
    assert statuses["CPSC"]["status"] == "ok"
    assert len(calls) <= 6
    assert all("Title" not in call for call in calls)
    assert len({item["recall_id"] for item in matches}) == len(matches)
    assert any(item["recall_id"] == "18-101" for item in matches)


def test_actor_publishes_full_result_record():
    from src.actor_template import run_actor_queries

    class FakeActor:
        rows = []
        async def push_data(self, row): self.rows.append(row)
        async def charge(self, **kwargs): pass
        async def set_status_message(self, *args, **kwargs): pass
    actor = FakeActor()
    result = {"outcome": "match", "message": "match", "query": {"product_name": "Rock 'n Play"},
              "matches": [{"recall_id": "18-101"}], "sources_checked": {"CPSC": {"status": "ok"}},
              "checked_at": "2026-10-10T00:00:00Z"}
    asyncio.run(run_actor_queries(actor, [result["query"]], check_one=lambda _query: result))
    assert actor.rows == [result]
    schema = json.loads((ROOT / ".actor/dataset_schema.json").read_text(encoding="utf-8"))
    result_fields = {"outcome", "message", "query", "matches", "sources_checked", "checked_at"}
    apify_schema_keys = {"actorSpecification", "title", "description", "fields", "views"}
    assert set(schema) <= apify_schema_keys
    assert result_fields <= set(schema["fields"]["properties"])
    overview_fields = schema["views"]["overview"]["transformation"]["fields"]
    assert result_fields <= set(overview_fields)


@pytest.mark.skipif(os.getenv("RECALL_LIVE") != "1", reason="set RECALL_LIVE=1 for public-source canary")
def test_live_rock_n_play_has_cpsc_match():
    from src.checker import check_one
    result = check_one({"brand": "Fisher-Price", "product_name": "Rock 'n Play Sleeper"})
    assert result["outcome"] == "match"
    assert any(m["source"] == "CPSC" and ("cpsc.gov" in m["url"] or "saferproducts.gov" in m["url"])
               for m in result["matches"])
