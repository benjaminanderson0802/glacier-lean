import json
import io
import sqlite3
import urllib.parse

from ventures.blocks.feeds import query, sync
from ventures.blocks.feeds.core import normalize_rows, store_snapshot


def test_normalize_produces_dated_rows_and_detects_format_changes():
    rows, alerts = normalize_rows(
        "fixture",
        [{"recall_number": "A-1", "title": "Example", "recall_date": "2026-01-02", "new_field": "x"}],
        source_url="https://example.test/data",
        fetched_at="2026-01-03T00:00:00Z",
    )
    assert rows == [{
        "source_id": "fixture",
        "record_id": "A-1",
        "record_date": "2026-01-02",
        "fetched_at": "2026-01-03T00:00:00Z",
        "source_url": "https://example.test/data",
        "data": {"recall_number": "A-1", "title": "Example", "recall_date": "2026-01-02", "new_field": "x"},
    }]
    assert any("new_field" in alert for alert in alerts)


def test_store_query_and_count_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    rows, _ = normalize_rows("fixture", [{"id": "one", "date": "2026-05-06"}], source_url="https://example.test", fetched_at="2026-05-07T00:00:00Z")
    db = tmp_path / "ventures" / "feeds.db"
    assert store_snapshot("fixture", rows, db_path=db, source_total=1) == 1
    got = query("fixture", db_path=db, record_id="one")
    assert len(got) == 1 and got[0]["record_date"] == "2026-05-06"
    with sqlite3.connect(db) as con:
        total, actual = con.execute("select source_total, row_count from feed_syncs").fetchone()
    assert total == actual == 1


def test_public_registry_has_all_requested_sources():
    from ventures.blocks.feeds import registry

    expected = {"cpsc_recalls", "cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template",
                "nhtsa_recalls", "fda_enforcement", "fsis_recalls", "osha_ita", "dla_dibbs", "cook_county_assessor"}
    assert expected <= set(registry())
    assert all(registry()[item].get("url") for item in expected)
    assert registry()["cpsc_recalls"]["kind"] == "cpsc_recalls_api"
    assert registry()["cpsc_recalls"]["history_start_year"] == 1973
    assert all(registry()[item]["kind"] == "cpsc_document" for item in
               ("cpsc_flagged_tariff_codes", "cpsc_rule_codes", "cpsc_registry_template"))


def test_fsis_public_api_request_uses_honest_json_headers(monkeypatch):
    from ventures.blocks.feeds import core

    def fake_urlopen(request, timeout):
        assert request.get_header("Referer") is None
        assert "application/json" in request.get_header("Accept")
        return io.BytesIO(b"[]")

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    records, total = core._json_rows(core.registry()["fsis_recalls"]["url"])
    assert records == [] and total is None


def test_request_uses_descriptive_client_and_retries_transient_http_errors(tmp_path, monkeypatch):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    calls = []

    class Response(io.BytesIO):
        headers = {"Content-Type": "application/json"}
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise core.urllib.error.HTTPError(request.full_url, 503, "busy", {}, None)
        return Response(b'{"ok":true}')

    waits = []
    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(core.time, "sleep", waits.append)
    assert core._request("https://example.test/data", timeout=7) == b'{"ok":true}'
    assert len(calls) == 2 and waits == [0.5]
    assert "Glacier" in calls[0][0].get_header("User-agent")
    assert "github.com/benjaminanderson0802/glacier-lean" in calls[0][0].get_header("User-agent")
    assert calls[0][1] == 7


def test_request_caches_small_public_responses_and_reuses_them(tmp_path, monkeypatch):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    calls = []

    class Response(io.BytesIO):
        headers = {"ETag": '"feed-v1"', "Content-Type": "application/json"}
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def fake_urlopen(request, timeout):
        calls.append(request)
        return Response(b'{"cached":true}')

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    assert core._request("https://example.test/cache") == b'{"cached":true}'
    assert core._request("https://example.test/cache") == b'{"cached":true}'
    assert len(calls) == 1


def test_cook_county_filter_is_scoped_and_uses_incremental_watermark():
    from ventures.blocks.feeds import registry

    config = registry()["cook_county_assessor"]
    assert config["selected_fields"] == ["pin", "year", "class", "township_code", "township_name", "zip_code", ":updated_at"]
    assert config["target_classes"] == ["211"]
    assert config["incremental_field"] == ":updated_at"


def test_cook_county_incremental_sync_uses_timestamp_watermark_and_upserts(tmp_path, monkeypatch):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    old = [{"source_id": "cook_county_assessor", "record_id": "001", "record_date": "2026-01-01",
            "fetched_at": "2026-01-01T00:00:00Z", "source_url": "https://example.test/roll",
            "data": {"pin": "001", "year": "2026", "class": "211", "township_code": "10", "zip_code": "60000", ":updated_at": "2026-01-01T00:00:00.000"}}]
    core.store_snapshot("cook_county_assessor", old, source_total=1)
    calls = []

    def fake_json_rows(url, timeout=30):
        calls.append(url)
        if "$offset=0" in url:
            return ([{"pin": "001", "year": "2026", "class": "211", "township_code": "10",
                      "township_name": "Barrington", "zip_code": "60000",
                      ":updated_at": "2026-01-02T00:00:00.000"}], None)
        return ([], None)

    monkeypatch.setattr(core, "_json_rows", fake_json_rows)
    result = core._sync_socrata_incremental(
        "cook_county_assessor", core.registry()["cook_county_assessor"],
        "year%3D'2026'", 1, "2026-01-01T00:00:00.000", "2026-01-03T00:00:00Z")
    assert result["rows"] == 1 and result["changed"] and result["complete"]
    assert len(calls) == 1
    assert ":updated_at%20%3E%20'2026-01-01T00:00:00.000'" in calls[0]
    assert core.query("cook_county_assessor")[0]["data"]["township_name"] == "Barrington"


def test_nhtsa_dictionary_uses_numbered_fields_instead_of_description_tabs():
    from ventures.blocks.feeds.core import _nhtsa_columns

    dictionary = """FIELDS:
1        RECORD_ID           NUMBER(9)   Unique identifier
2        CAMPNO              CHAR(12)    Recall number
16       RCDATE              CHAR(8)     Received date
"""
    # A malformed sequence must be rejected instead of silently shifting columns.
    try:
        _nhtsa_columns(dictionary)
    except ValueError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("incomplete NHTSA field dictionary was accepted")

    full_dictionary = "\n".join(
        f"{i}       {name}              CHAR(8)    Description" for i, name in enumerate(
            ["RECORD_ID", "CAMPNO", "MAKETXT", "MODELTXT", "YEARTXT", "MFGCAMPNO", "COMPNAME", "MFGNAME", "BGMAN", "ENDMAN", "RCLTYPECD", "POTAFF", "ODATE", "INFLUENCED_BY", "MFGTXT", "RCDATE", "DATEA", "RPNO", "FMVSS", "DESC_DEFECT", "CONEQUENCE_DEFECT", "CORRECTIVE_ACTION", "NOTES", "RCL_CMPT_ID", "MFR_COMP_NAME", "MFR_COMP_DESC", "MFR_COMP_PTNO", "DO_NOT_DRIVE", "PARK_OUTSIDE"], 1))
    assert _nhtsa_columns(full_dictionary)[1] == "CAMPNO"
    assert _nhtsa_columns(full_dictionary)[15] == "RCDATE"
    assert _nhtsa_columns(full_dictionary)[28] == "PARK_OUTSIDE"


def test_composite_identifier_keeps_fda_categories_with_reused_recall_numbers(monkeypatch, tmp_path):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(core, "registry", lambda: {"fixture": {"id_fields": ["recall_number"], "composite_id_fields": ["dataset", "recall_number"]}})
    rows, alerts = core.normalize_rows(
        "fixture",
        [{"dataset": "Food", "recall_number": "F-1"}, {"dataset": "Drug", "recall_number": "F-1"}],
        source_url="https://example.test",
    )
    assert [row["record_id"] for row in rows] == ["Food|F-1", "Drug|F-1"]
    assert not alerts


def test_sync_uses_adapter_and_canary(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    from ventures.blocks.feeds import core

    monkeypatch.setattr(core, "fetch_source", lambda source_id, config: ([{"RecallNumber": "canary-1", "RecallDate": "2026-01-01", "RecallTitle": "Recall"}], 1, []))
    result = sync("cpsc_recalls")
    assert result["rows"] == 1
    assert result["changed"] is True
    assert not result["alerts"]
    again = sync("cpsc_recalls")
    assert again["changed"] is False
    assert query("cpsc_recalls", record_id="canary-1")


def test_format_alert_on_schema_change(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    from ventures.blocks.feeds import core

    payload = [{"RecallNumber": "canary-1", "RecallDate": "2026-01-01", "RecallTitle": "Recall"}]
    monkeypatch.setattr(core, "fetch_source", lambda source_id, config: (payload, None, []))
    sync("cpsc_recalls")
    payload[:] = [{"RecallNumber": "canary-2", "RecallDate": "2026-01-02", "new_shape": True}]
    result = sync("cpsc_recalls")
    assert result["alerts"] and any("format" in alert.lower() for alert in result["alerts"])


def test_daily_flow_syncs_every_registered_source():
    from pathlib import Path

    flow = json.loads((Path(__file__).parents[1] / "flows" / "daily_sync.json").read_text())
    assert any(node["type"] == "schedule" and node["config"].get("cron") == "0 2 * * *" for node in flow["nodes"])
    commands = "\n".join(node.get("config", {}).get("cmd", "") for node in flow["nodes"])
    assert "sync-all" in commands


def test_socrata_sync_resumes_in_bounded_pages_and_keeps_progress_visible(tmp_path, monkeypatch):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    old_rows = [{"source_id": "fixture_roll", "record_id": "old", "record_date": "2024-01-01",
                 "fetched_at": "2024-01-01T00:00:00Z", "source_url": "https://example.test/old",
                 "data": {"pin": "old", "year": "2024", "class": "2-11"}}]
    core.store_snapshot("fixture_roll", old_rows, source_total=1)
    calls = []

    def fake_json_rows(url, timeout=45):
        calls.append(url)
        if "$select=max(year)" in url:
            return ([{"max_year": "2025"}], None)
        if "$select=max(:updated_at)" in url:
            return ([{"max_updated_at": "2025-02-01T00:00:00.000"}], None)
        if "$select=count(*)" in url:
            return ([{"count": "5"}], None)
        offset = int(url.rsplit("$offset=", 1)[1])
        return ([{"pin": str(i), "year": "2025", "class": "2-11"}
                 for i in range(offset, min(offset + 2, 5))], None)

    monkeypatch.setattr(core, "_json_rows", fake_json_rows)
    config = {"url": "https://example.test/roll", "selected_fields": ["pin", "year", "class"],
              "id_fields": ["pin"], "date_fields": ["year"], "expected_fields": ["pin"],
              "canary": {"field": "pin"}, "target_township_codes": ["11"],
              "target_classes": ["2-11"], "page_size": 2, "max_pages_per_sync": 1}

    first = core._sync_socrata_stream("fixture_roll", config)
    assert first["complete"] is False
    assert first["progress"] == {"downloaded": 2, "total": 5, "tax_year": "2025"}
    assert "progress" in " ".join(first["alerts"]).lower()
    assert [row["record_id"] for row in core.query("fixture_roll")] == ["old"]

    config["max_pages_per_sync"] = 2
    second = core._sync_socrata_stream("fixture_roll", config)
    assert second["complete"] is True
    assert second["rows"] == 5
    assert len(core.query("fixture_roll")) == 5
    assert "old" not in [row["record_id"] for row in core.query("fixture_roll")]
    assert len([url for url in calls if "$offset=" in url]) == 3
    assert all("township_code in ('11')" in urllib.parse.unquote(url) for url in calls if "$select=count(*)" in url)
    assert all("class in ('2-11')" in urllib.parse.unquote(url) for url in calls if "$offset=" in url)


def test_dibbs_warning_redirect_is_reported_with_manual_intake_instructions(tmp_path, monkeypatch):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(core, "registry", lambda: {"fixture_dibbs": {"kind": "dibbs_html", "url": "https://www.dibbs.bsm.dla.mil/Solicitations/"}})
    monkeypatch.setattr(core, "_request", lambda url: b"<html><title>DoD Warning and Consent Banner</title><body>warning consent</body></html>")
    result = core.sync("fixture_dibbs")
    message = " ".join(result["alerts"]).lower()
    assert result["rows"] == 0
    assert "warning" in message and "owner" in message and "official solicitation" in message
