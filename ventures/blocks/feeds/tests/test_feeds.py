import json
import io
import sqlite3

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

    expected = {"cpsc_recalls", "nhtsa_recalls", "fda_enforcement", "fsis_recalls", "osha_ita", "dla_dibbs", "cook_county_assessor"}
    assert expected <= set(registry())
    assert all(registry()[item].get("url") for item in expected)
    assert "RecallDateStart=1973-01-01" in registry()["cpsc_recalls"]["url"]


def test_fsis_public_api_request_uses_official_same_site_referer(monkeypatch):
    from ventures.blocks.feeds import core

    def fake_urlopen(request, timeout):
        assert request.get_header("Referer") == "https://www.fsis.usda.gov/recalls"
        assert request.get_header("Accept") == "application/json"
        return io.BytesIO(b"[]")

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    records, total = core._json_rows(core.registry()["fsis_recalls"]["url"])
    assert records == [] and total is None


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

    monkeypatch.setattr(core, "fetch_source", lambda source_id, config: ([{"id": "canary-1", "date": "2026-01-01", "title": "Recall"}], 1, []))
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

    payload = [{"id": "canary-1", "date": "2026-01-01", "title": "Recall"}]
    monkeypatch.setattr(core, "fetch_source", lambda source_id, config: (payload, None, []))
    sync("cpsc_recalls")
    payload[:] = [{"id": "canary-2", "date": "2026-01-02", "new_shape": True}]
    result = sync("cpsc_recalls")
    assert result["alerts"] and any("format" in alert.lower() for alert in result["alerts"])


def test_daily_flow_syncs_every_registered_source():
    from pathlib import Path

    flow = json.loads((Path(__file__).parents[1] / "flows" / "daily_sync.json").read_text())
    assert any(node["type"] == "schedule" and node["config"].get("cron") == "0 2 * * *" for node in flow["nodes"])
    commands = "\n".join(node.get("config", {}).get("cmd", "") for node in flow["nodes"])
    assert "sync-all" in commands
