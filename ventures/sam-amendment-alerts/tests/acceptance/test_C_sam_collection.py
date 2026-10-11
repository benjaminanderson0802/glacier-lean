"""Independent acceptance checks for bounded SAM API snapshot collection.

The fixtures below are frozen API v2 response pages.  They intentionally test
the public collector-to-digest handoff, not collector helper functions.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

import pytest


KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load_collector():
    path = SCRIPTS / "collect_snapshot.py"
    spec = importlib.util.spec_from_file_location("sam_collection_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import digest

collector = _load_collector()

API_URL = "https://api.sam.gov/opportunities/v2/search"
FIXTURE_KEY = "fixture-only-sam-key"
CAPTURE_TIME = datetime(2026, 10, 11, 14, 30, tzinfo=timezone.utc)


def _notice(notice_id: str, *, deadline: str = "2026-11-03T16:00:00Z") -> dict:
    return {
        "noticeId": notice_id,
        "title": f"Frozen API fixture {notice_id}",
        "solicitationNumber": f"SOL-{notice_id}",
        "naicsCode": "423840",
        "responseDeadLine": deadline,
        "uiLink": f"https://sam.gov/opp/{notice_id}/view",
        "links": [{"rel": "self", "href": f"https://sam.gov/opp/{notice_id}/view"}],
    }


def _api_page(offset: int, rows: list[dict], *, total: int, limit: int = 2) -> dict:
    """Documented v2 page envelope: totalRecords, limit, offset, opportunitiesData."""
    return {"totalRecords": total, "limit": limit, "offset": offset, "opportunitiesData": rows}


def _collect(pages: dict[int, dict], output: Path, *, codes=("423840",), **kwargs) -> dict:
    calls = []

    def frozen_request(params, key):
        assert key == FIXTURE_KEY
        calls.append(dict(params))
        return pages[params["offset"]]

    snapshot = collector.collect_snapshot(
        naics_codes=list(codes),
        output_path=output,
        api_key=FIXTURE_KEY,
        request_json=frozen_request,
        now=CAPTURE_TIME,
        **kwargs,
    )
    return snapshot


def test_frozen_pages_are_saved_exactly_with_bounds_scope_and_provenance(tmp_path):
    """Acceptance first: all fixture rows and capture metadata survive collection."""
    page_zero = _api_page(0, [_notice("N-1"), _notice("N-2")], total=3)
    page_two = _api_page(2, [_notice("N-3")], total=3)
    target = tmp_path / "captured.json"

    snapshot = _collect(
        {0: page_zero, 2: page_two}, target, page_size=2, max_pages=2, max_records=3
    )

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved == snapshot
    assert saved["opportunitiesData"] == page_zero["opportunitiesData"] + page_two["opportunitiesData"]
    assert saved["query_scope"] == {"naics_codes": ["423840"]}
    assert saved["source_url"] == API_URL
    assert saved["retrieved_at"] == "2026-10-11T14:30:00Z"
    assert saved["retrieval_date"] == "2026-10-11"
    assert saved["complete"] is True and saved["status"] == "complete"
    assert saved["pages_fetched"] == 2 and saved["record_count"] == 3
    assert saved["total_records"] == 3 and saved["limit"] == 2 and saved["offset"] == 0


def test_collector_snapshot_hands_unchanged_rows_to_digest(tmp_path):
    """The collector's output is directly consumable; row contents must be preserved."""
    before = _collect(
        {0: _api_page(0, [_notice("N-1")], total=1)},
        tmp_path / "before.json", page_size=2, max_pages=2, max_records=2,
    )
    after_pages = {
        0: _api_page(0, [_notice("N-1"), _notice("N-2")], total=3),
        2: _api_page(2, [_notice("N-3")], total=3),
    }
    after = _collect(
        after_pages, tmp_path / "after.json", page_size=2, max_pages=2, max_records=3,
    )

    assert after["opportunitiesData"] == after_pages[0]["opportunitiesData"] + after_pages[2]["opportunitiesData"]
    result = digest.build_digest(before, after, naics_codes={"423840"})
    assert result["status"] == "match"
    assert [event["notice_id"] for event in result["events"]] == ["N-2", "N-3"]
    assert "does not reconstruct amendments published before the first snapshot" in result["coverage_note"]


@pytest.mark.parametrize(
    "pages, bounds, error_pattern",
    [
        ({0: _api_page(0, [_notice("N-1"), _notice("N-2")], total=3)}, {"max_pages": 1}, "incomplete|bound"),
        ({0: _api_page(0, [_notice("N-1"), _notice("N-2")], total=3),
          2: _api_page(2, [_notice("N-3")], total=4)}, {}, "totalRecords|partial"),
        ({0: _api_page(0, [_notice("N-1"), _notice("N-2")], total=3),
          2: {"totalRecords": 3, "limit": 2, "offset": 2, "opportunitiesData": None}},
         {}, "partial|malformed"),
        ({0: _api_page(0, [_notice("N-1"), _notice("N-1")], total=2)}, {}, "duplicate"),
    ],
)
def test_partial_pages_and_duplicate_conflicts_never_save_a_complete_snapshot(
    tmp_path, pages, bounds, error_pattern
):
    target = tmp_path / "must-not-exist.json"
    with pytest.raises(ValueError, match=error_pattern):
        options = {"page_size": 2, "max_pages": 2, "max_records": 10} | bounds
        _collect(pages, target, **options)
    assert not target.exists()


def test_conflicting_duplicate_across_selected_naics_queries_fails_closed(tmp_path):
    target = tmp_path / "conflict.json"

    def response(params, key):
        code = params["ncode"]
        row = _notice("SHARED")
        row["naicsCode"] = code
        row["title"] = f"different representation for {code}"
        return _api_page(0, [row], total=1, limit=1)

    with pytest.raises(ValueError, match="conflicting duplicate"):
        collector.collect_snapshot(
            naics_codes=["423840", "423830"], output_path=target, api_key=FIXTURE_KEY,
            request_json=response, page_size=1, max_pages=2, max_records=4, now=CAPTURE_TIME,
        )
    assert not target.exists()


@pytest.mark.parametrize("error", [HTTPError(API_URL, 429, "rate limit", {}, None), {"error": "unavailable"}])
def test_api_errors_are_explicit_and_do_not_replace_a_saved_snapshot(tmp_path, error):
    target = tmp_path / "existing.json"
    target.write_text('{"trusted": true}\n', encoding="utf-8")

    def response(params, key):
        if isinstance(error, HTTPError):
            raise error
        return error

    with pytest.raises(ValueError):
        collector.collect_snapshot(
            naics_codes=["423840"], output_path=target, api_key=FIXTURE_KEY,
            request_json=response, page_size=2, max_pages=2, max_records=4, now=CAPTURE_TIME,
        )
    assert json.loads(target.read_text(encoding="utf-8")) == {"trusted": True}


def test_missing_deadline_stays_uncertain_in_digest_when_snapshot_contract_is_valid():
    before = {
        "retrieved_at": "2026-10-10T12:00:00Z", "source_url": API_URL,
        "naics_codes": ["423840"], "totalRecords": 0, "limit": 2, "offset": 0,
        "page_coverage": [], "opportunitiesData": [],
    }
    current = _notice("NO-DEADLINE")
    current.pop("responseDeadLine")
    after = {
        "retrieved_at": "2026-10-11T12:00:00Z", "source_url": API_URL,
        "naics_codes": ["423840"], "totalRecords": 1, "limit": 2, "offset": 0,
        "page_coverage": [{"offset": 0, "count": 1}], "opportunitiesData": [current],
    }

    result = digest.build_digest(before, after, naics_codes={"423840"})
    assert result["status"] == digest.UNCERTAIN
    assert len(result["events"]) == 1 and result["events"][0]["uncertain"] is True
    assert "does not reconstruct amendments published before the first snapshot" in result["coverage_note"]
