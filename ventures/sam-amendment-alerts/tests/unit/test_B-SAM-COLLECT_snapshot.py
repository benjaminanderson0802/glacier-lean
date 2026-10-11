"""Offline fixture checks for bounded SAM snapshot intake."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

import pytest


KIT = Path(__file__).resolve().parents[2]
MODULE_PATH = KIT / "scripts" / "collect_snapshot.py"
SPEC = importlib.util.spec_from_file_location("collect_snapshot", MODULE_PATH)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(collector)


API_URL = "https://api.sam.gov/opportunities/v2/search"
FIXED_TIME = datetime(2026, 10, 11, 14, 30, tzinfo=timezone.utc)
SECRET = "fixture-secret-do-not-persist"


def page(offset: int, rows: list[dict], *, total: int, limit: int = 2) -> dict:
    return {
        "totalRecords": total,
        "limit": limit,
        "offset": offset,
        "opportunitiesData": rows,
    }


def notice(notice_id: str, naics: str = "423840") -> dict:
    return {
        "noticeId": notice_id,
        "naicsCode": naics,
        "title": f"Fixture notice {notice_id}",
        "uiLink": f"https://sam.gov/opp/{notice_id}/view",
    }


def test_successful_multipage_snapshot_records_complete_scope_and_provenance(tmp_path):
    responses = {
        0: page(0, [notice("one"), notice("two")], total=3),
        2: page(2, [notice("three")], total=3),
    }
    calls = []

    def request_json(params, api_key):
        calls.append((dict(params), api_key))
        return responses[params["offset"]]

    output = tmp_path / "snapshot.json"
    result = collector.collect_snapshot(
        naics_codes=["423840"],
        output_path=output,
        api_key=SECRET,
        request_json=request_json,
        page_size=2,
        max_pages=3,
        max_records=10,
        now=FIXED_TIME,
    )

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved == result
    assert saved["complete"] is True
    assert saved["status"] == "complete"
    assert [row["noticeId"] for row in saved["opportunitiesData"]] == ["one", "two", "three"]
    assert saved["query_scope"] == {"naics_codes": ["423840"]}
    assert saved["retrieved_at"] == "2026-10-11T14:30:00Z"
    assert saved["retrieval_date"] == "2026-10-11"
    assert saved["source_url"] == API_URL
    assert saved["pages_fetched"] == 2
    assert saved["record_count"] == 3
    assert [(call[0]["ncode"], call[0]["offset"], call[0]["limit"]) for call in calls] == [
        ("423840", 0, 2),
        ("423840", 2, 2),
    ]
    assert all(call[1] == SECRET for call in calls)
    assert SECRET not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("failed_offset", [0, 2])
def test_quota_error_fails_without_saving_partial_snapshot(tmp_path, failed_offset):
    output = tmp_path / "snapshot.json"
    calls = []

    def request_json(params, api_key):
        calls.append(params["offset"])
        if params["offset"] == failed_offset:
            raise HTTPError(API_URL, 429, "rate limit exceeded", {}, None)
        return page(0, [notice("first"), notice("second")], total=3)

    with pytest.raises(ValueError, match="(?i)(quota|rate limit)") as error:
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            api_key=SECRET,
            request_json=request_json,
            page_size=2,
            max_pages=3,
            max_records=10,
            now=FIXED_TIME,
        )

    assert not output.exists()
    assert SECRET not in str(error.value)
    assert SECRET not in " ".join(map(str, calls))


def test_malformed_later_page_fails_without_saving_partial_snapshot(tmp_path):
    output = tmp_path / "snapshot.json"

    def request_json(params, api_key):
        if params["offset"] == 0:
            return page(0, [notice("first"), notice("second")], total=3)
        return {"totalRecords": 3, "limit": 2, "offset": 2, "opportunitiesData": None}

    with pytest.raises(ValueError, match="(?i)(partial|malformed|unexpected)"):
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            api_key=SECRET,
            request_json=request_json,
            page_size=2,
            max_pages=3,
            max_records=10,
            now=FIXED_TIME,
        )

    assert not output.exists()


def test_page_bound_truncation_fails_without_saving_partial_snapshot(tmp_path):
    output = tmp_path / "snapshot.json"

    def request_json(params, api_key):
        return page(params["offset"], [notice("first"), notice("second")], total=5)

    with pytest.raises(ValueError, match="(?i)(truncat|bound|incomplete)"):
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            api_key=SECRET,
            request_json=request_json,
            page_size=2,
            max_pages=1,
            max_records=10,
            now=FIXED_TIME,
        )

    assert not output.exists()


def test_missing_glacier_secret_fails_before_request_with_setup_guidance(tmp_path, monkeypatch):
    output = tmp_path / "snapshot.json"
    requests = []
    monkeypatch.setattr(
        collector,
        "_resolve_sam_api_key",
        lambda: (_ for _ in ()).throw(ValueError("SAM.gov API key is required. Save it in Glacier Settings → Secrets, then retry.")),
    )

    with pytest.raises(ValueError, match="(?i)(SAM.gov API key|Settings.*Secrets|retry)"):
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            request_json=lambda *args: requests.append(args),
            now=FIXED_TIME,
        )

    assert requests == []
    assert not output.exists()


def test_secret_echoed_in_source_record_is_redacted_before_persistence(tmp_path):
    output = tmp_path / "snapshot.json"
    unsafe = notice("echoed-secret")
    unsafe["uiLink"] = f"https://sam.gov/opp/echoed-secret/view?api_key={SECRET}"
    unsafe["api_key"] = SECRET
    unsafe["description"] = f"provider echo: {SECRET}"

    collector.collect_snapshot(
        naics_codes=["423840"],
        output_path=output,
        api_key=SECRET,
        request_json=lambda params, api_key: page(0, [unsafe], total=1),
        page_size=2,
        max_pages=3,
        max_records=10,
        now=FIXED_TIME,
    )

    saved_text = output.read_text(encoding="utf-8")
    saved_notice = json.loads(saved_text)["opportunitiesData"][0]
    assert SECRET not in saved_text
    assert "api_key" not in saved_notice
    assert "api_key=" not in saved_notice["uiLink"]
    assert "[REDACTED]" in saved_notice["description"]


def test_record_bound_fails_closed_when_provider_has_more_results(tmp_path):
    output = tmp_path / "snapshot.json"

    with pytest.raises(ValueError, match="(?i)(record|truncat|incomplete|bound)"):
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            api_key=SECRET,
            request_json=lambda params, api_key: page(0, [notice("one"), notice("two")], total=3),
            page_size=2,
            max_pages=3,
            max_records=2,
            now=FIXED_TIME,
        )

    assert not output.exists()


def test_page_bound_applies_to_all_selected_naics_queries(tmp_path):
    output = tmp_path / "snapshot.json"

    def request_json(params, api_key):
        if params["ncode"] == "423840":
            return page(0, [notice("one", "423840")], total=1)
        if params["offset"] == 0:
            return page(0, [notice("two", "423830"), notice("three", "423830")], total=3)
        return page(2, [notice("four", "423830")], total=3)

    with pytest.raises(ValueError, match="(?i)(page bound|incomplete|truncat)"):
        collector.collect_snapshot(
            naics_codes=["423840", "423830"],
            output_path=output,
            api_key=SECRET,
            request_json=request_json,
            page_size=2,
            max_pages=2,
            max_records=10,
            now=FIXED_TIME,
        )

    assert not output.exists()


def test_duplicate_notice_within_one_naics_query_is_rejected(tmp_path):
    output = tmp_path / "snapshot.json"
    duplicate = notice("duplicate")

    with pytest.raises(ValueError, match="(?i)(duplicate|incomplete|partial)"):
        collector.collect_snapshot(
            naics_codes=["423840"],
            output_path=output,
            api_key=SECRET,
            request_json=lambda params, api_key: page(0, [duplicate, dict(duplicate)], total=2),
            page_size=2,
            max_pages=3,
            max_records=10,
            now=FIXED_TIME,
        )

    assert not output.exists()
