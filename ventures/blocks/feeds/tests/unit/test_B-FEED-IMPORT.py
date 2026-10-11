import hashlib
import io
import json
import sqlite3
import zipfile

from ventures.blocks.feeds import core, query
from ventures.blocks.feeds.import_snapshot import import_snapshot


def write_json(path, records, total=None):
    payload = {"results": records}
    if total is not None:
        payload["total"] = total
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_saved_official_json_import_records_provenance_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    source_file = write_json(tmp_path / "fsis.json", [
        {"field_recall_number": "FSIS-1", "field_recall_date": "2026-10-10", "field_title": "Recall"}
    ], total=1)
    source_url = "https://www.fsis.usda.gov/news-events/news-feeds-subscriptions"

    first = import_snapshot("fsis_recalls", source_file, source_url=source_url, acquired_at="2026-10-10", complete=True)
    second = import_snapshot("fsis_recalls", source_file, source_url=source_url, acquired_at="2026-10-10", complete=True)

    assert first["status"] == "ok" and first["changed"] is True
    assert first["live_fetch"] is False and first["complete"] is True
    assert second["status"] == "ok" and second["changed"] is False
    rows = query("fsis_recalls")
    assert len(rows) == 1 and rows[0]["record_id"] == "FSIS-1"
    assert rows[0]["source_url"] == source_url
    with sqlite3.connect(tmp_path / "glacier" / "ventures" / "feeds.db") as con:
        provenance = con.execute(
            "SELECT source_url, acquired_at, sha256, format, row_count, complete FROM feed_imports WHERE source_id='fsis_recalls'"
        ).fetchone()
    assert provenance == (source_url, "2026-10-10", hashlib.sha256(source_file.read_bytes()).hexdigest(), "json", 1, 1)


def test_invalid_stale_incomplete_and_html_error_imports_retain_trusted_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    source_url = "https://www.fsis.usda.gov/news-events/news-feeds-subscriptions"
    good = write_json(tmp_path / "good.json", [
        {"field_recall_number": "GOOD-1", "field_recall_date": "2026-10-10", "field_title": "Good"}
    ], total=1)
    assert import_snapshot("fsis_recalls", good, source_url=source_url, acquired_at="2026-10-10", complete=True)["status"] == "ok"
    before = query("fsis_recalls")
    database = tmp_path / "glacier" / "ventures" / "feeds.db"
    with sqlite3.connect(database) as con:
        before_schema = con.execute("SELECT fields FROM feed_schemas WHERE source_id='fsis_recalls'").fetchone()[0]
        before_hash = con.execute("SELECT sha256 FROM feed_imports WHERE source_id='fsis_recalls'").fetchone()[0]

    malformed = tmp_path / "malformed.json"
    malformed.write_text("<html><title>403 Forbidden</title></html>", encoding="utf-8")
    stale = write_json(tmp_path / "stale.json", [
        {"field_recall_number": "OLD-1", "field_recall_date": "2010-01-01", "field_title": "Old"}
    ], total=1)
    incomplete = write_json(tmp_path / "partial.json", [
        {"field_recall_number": "PART-1", "field_recall_date": "2026-10-10", "field_title": "Partial"}
    ], total=1)
    count_mismatch = write_json(tmp_path / "count-mismatch.json", [
        {"field_recall_number": "COUNT-1", "field_recall_date": "2026-10-10", "field_title": "Mismatch"}
    ], total=100)
    missing_canary = write_json(tmp_path / "missing-canary.json", [
        {"field_recall_date": "2026-10-10", "field_title": "No identifier"}
    ], total=1)
    changed_schema = write_json(tmp_path / "changed-schema.json", [
        {"field_recall_number": "SCHEMA-1", "field_recall_date": "2026-10-10", "other": "Changed"}
    ], total=1)

    cases = [
        import_snapshot("fsis_recalls", malformed, source_url=source_url, acquired_at="2026-10-10", complete=True),
        import_snapshot("fsis_recalls", stale, source_url=source_url, acquired_at="2020-01-01", complete=True),
        import_snapshot("fsis_recalls", incomplete, source_url=source_url, acquired_at="2026-10-10", complete=False),
        import_snapshot("fsis_recalls", count_mismatch, source_url=source_url, acquired_at="2026-10-10", complete=True),
        import_snapshot("fsis_recalls", missing_canary, source_url=source_url, acquired_at="2026-10-10", complete=True),
        import_snapshot("fsis_recalls", changed_schema, source_url=source_url, acquired_at="2026-10-10", complete=True),
    ]

    assert all(result["status"] == "failed" and result["changed"] is False for result in cases)
    assert query("fsis_recalls") == before
    with sqlite3.connect(database) as con:
        assert con.execute("SELECT fields FROM feed_schemas WHERE source_id='fsis_recalls'").fetchone()[0] == before_schema
        assert con.execute("SELECT sha256 FROM feed_imports WHERE source_id='fsis_recalls'").fetchone()[0] == before_hash


def test_osha_csv_and_dibbs_html_use_existing_source_schemas(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    csv_file = tmp_path / "osha.csv"
    csv_file.write_text(
        "establishment_id,establishment_name,city,state,industry_description\n123,Example,Chicago,IL,Manufacturing\n",
        encoding="utf-8",
    )
    csv_result = import_snapshot(
        "osha_ita", csv_file, source_url="https://www.osha.gov/itadata", acquired_at="2026-10-10", complete=True
    )
    assert csv_result["status"] == "ok" and csv_result["format"] == "csv"
    assert query("osha_ita")[0]["record_id"] == "123"

    html_file = tmp_path / "dibbs.html"
    html_file.write_text(
        '<html><body><a href="/rfq/ABC123456">Public solicitation</a></body></html>', encoding="utf-8"
    )
    html_result = import_snapshot(
        "dla_dibbs", html_file, source_url="https://www.dibbs.bsm.dla.mil/rfq/ABC123456",
        acquired_at="2026-10-10", complete=True,
    )
    assert html_result["status"] == "ok" and html_result["format"] == "html"
    assert query("dla_dibbs")[0]["source_url"].endswith("ABC123456")

    consent_file = tmp_path / "consent.html"
    consent_file.write_text("<html><title>DoD Warning and Consent</title></html>", encoding="utf-8")
    rejected = import_snapshot(
        "dla_dibbs", consent_file, source_url="https://www.dibbs.bsm.dla.mil/rfq/ABC123456",
        acquired_at="2026-10-10", complete=True,
    )
    assert rejected["status"] == "failed"
    assert query("dla_dibbs")[0]["record_id"] == "ABC123456"


def test_successful_network_refresh_replaces_offline_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    source_url = "https://www.fsis.usda.gov/news-events/news-feeds-subscriptions"
    saved = write_json(tmp_path / "fsis.json", [
        {"field_recall_number": "FSIS-1", "field_recall_date": "2026-10-10", "field_title": "Saved"}
    ], total=1)
    import_snapshot("fsis_recalls", saved, source_url=source_url, acquired_at="2026-10-10", complete=True)
    monkeypatch.setattr(core, "fetch_source", lambda *_: ([
        {"field_recall_number": "FSIS-2", "field_recall_date": "2026-10-11", "field_title": "Refreshed"}
    ], 1, []))

    result = core.sync("fsis_recalls")

    assert result["status"] == "ok" and result["changed"] is True
    assert [row["record_id"] for row in query("fsis_recalls")] == ["FSIS-2"]
    with sqlite3.connect(tmp_path / "glacier" / "ventures" / "feeds.db") as con:
        assert con.execute("SELECT 1 FROM feed_imports WHERE source_id='fsis_recalls'").fetchone() is None


def test_openfda_zip_partition_import_uses_official_download_host(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    raw_zip = io.BytesIO()
    with zipfile.ZipFile(raw_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("food-enforcement.json", json.dumps({"results": [{
            "recall_number": "FDA-1", "report_date": "20261010", "product_description": "Example",
            "reason_for_recall": "Synthetic fixture",
        }]}))
    source_file = tmp_path / "fda.zip"
    source_file.write_bytes(raw_zip.getvalue())

    result = import_snapshot(
        "fda_enforcement", source_file,
        source_url="https://download.open.fda.gov/food/enforcement/2026.zip",
        acquired_at="2026-10-10", complete=True,
    )

    assert result["status"] == "ok" and result["format"] == "zip"
    assert query("fda_enforcement")[0]["record_id"] == "FDA-1"
