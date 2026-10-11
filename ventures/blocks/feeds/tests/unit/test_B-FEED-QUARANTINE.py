import json

import pytest

from ventures.blocks.feeds import core, query


@pytest.mark.parametrize(
    ("records", "source_total", "expected_alert"),
    [
        ([{"RecallNumber": "candidate", "RecallDate": "2026-02-01", "RecallTitle": "suspect"}], 100, "row-count"),
        ([{"RecallDate": "2026-02-01", "RecallTitle": "suspect"}], 1, "canary"),
        ([{"RecallNumber": "candidate", "RecallDate": "2026-02-01"}], 1, "schema changed"),
    ],
)
def test_suspect_candidate_keeps_trusted_snapshot_and_schema(tmp_path, monkeypatch, records, source_total, expected_alert):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    candidate = {"records": [{"RecallNumber": "trusted", "RecallDate": "2026-01-01", "RecallTitle": "trusted row"}], "total": 1}
    monkeypatch.setattr(core, "fetch_source", lambda _source, _config: (candidate["records"], candidate["total"], []))

    accepted = core.sync("cpsc_recalls")
    before_rows = query("cpsc_recalls")
    with core._connect() as con:
        before_schema = con.execute("SELECT fields FROM feed_schemas WHERE source_id='cpsc_recalls'").fetchone()[0]
    assert accepted["status"] == "ok"

    candidate.update(records=records, total=source_total)
    result = core.sync("cpsc_recalls")

    assert result["status"] == "failed"
    assert result["snapshot_available"] is True
    assert result["changed"] is False
    assert any(expected_alert in alert.lower() for alert in result["alerts"])
    assert query("cpsc_recalls") == before_rows
    with core._connect() as con:
        after_schema = con.execute("SELECT fields FROM feed_schemas WHERE source_id='cpsc_recalls'").fetchone()[0]
    assert json.loads(after_schema) == json.loads(before_schema)


def test_valid_replacement_promotes_rows_and_schema_together(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    candidate = {"records": [{"RecallNumber": "trusted", "RecallDate": "2026-01-01", "RecallTitle": "trusted row"}], "total": 1}
    monkeypatch.setattr(core, "fetch_source", lambda _source, _config: (candidate["records"], candidate["total"], []))
    core.sync("cpsc_recalls")

    candidate.update(records=[{"RecallNumber": "replacement", "RecallDate": "2026-02-01", "RecallTitle": "new row"}], total=1)
    result = core.sync("cpsc_recalls")

    assert result["status"] == "ok"
    assert result["changed"] is True
    assert [row["record_id"] for row in query("cpsc_recalls")] == ["replacement"]
    with core._connect() as con:
        schema = json.loads(con.execute("SELECT fields FROM feed_schemas WHERE source_id='cpsc_recalls'").fetchone()[0])
    assert schema == ["RecallDate", "RecallNumber", "RecallTitle"]


def test_failed_schema_write_rolls_back_replacement_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    candidate = {"records": [{"RecallNumber": "trusted", "RecallDate": "2026-01-01", "RecallTitle": "trusted row"}], "total": 1}
    monkeypatch.setattr(core, "fetch_source", lambda _source, _config: (candidate["records"], candidate["total"], []))
    core.sync("cpsc_recalls")
    trusted_rows = query("cpsc_recalls")

    candidate.update(records=[{"RecallNumber": "replacement", "RecallDate": "2026-02-01", "RecallTitle": "new row"}], total=1)

    def fail_schema_write(_con, _source_id, _fields):
        raise RuntimeError("injected promotion failure")

    monkeypatch.setattr(core, "_remember_schema", fail_schema_write)
    result = core.sync("cpsc_recalls")

    assert result["status"] == "failed"
    assert query("cpsc_recalls") == trusted_rows
    with core._connect() as con:
        schema = json.loads(con.execute("SELECT fields FROM feed_schemas WHERE source_id='cpsc_recalls'").fetchone()[0])
    assert schema == ["RecallDate", "RecallNumber", "RecallTitle"]


def test_failed_first_import_is_distinguished_from_retained_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(core, "fetch_source", lambda _source, _config: ([{"RecallDate": "2026-01-01"}], 1, []))

    result = core.sync("cpsc_recalls")

    assert result["status"] == "failed_initial"
    assert result["snapshot_available"] is False
    assert result["rows"] == 0
    assert query("cpsc_recalls") == []
    with core._connect() as con:
        assert con.execute("SELECT fields FROM feed_schemas WHERE source_id='cpsc_recalls'").fetchone() is None
