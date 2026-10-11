import io
import json
import urllib.error

import pytest


def test_fsis_request_uses_documented_client_id_and_parses_dated_records(monkeypatch, tmp_path):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    payload = [{
        "field_recall_number": "FSIS-2026-001",
        "field_recall_date": "2026-10-10",
        "field_title": "Example recall",
        "field_summary": "Fixture recall summary",
    }]

    def fake_urlopen(request, timeout):
        assert request.get_header("User-agent") == "Glacier public-data client"
        assert "application/json" in request.get_header("Accept")
        assert request.get_header("Referer") is None
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    records, total, alerts = core.fetch_source("fsis_recalls", core.registry()["fsis_recalls"])
    rows, normalize_alerts = core.normalize_rows(
        "fsis_recalls", records,
        source_url=core.registry()["fsis_recalls"]["url"],
        fetched_at="2026-10-11T00:00:00Z",
    )

    assert total is None
    assert alerts == [] and normalize_alerts == []
    assert len(rows) == 1
    assert rows[0]["record_id"] == "FSIS-2026-001"
    assert rows[0]["record_date"] == "2026-10-10"
    assert rows[0]["data"]["field_title"] == "Example recall"


@pytest.mark.parametrize("failure", [
    urllib.error.HTTPError("https://www.fsis.usda.gov/fsis/api/recall/v/1", 403, "Forbidden", {}, None),
    TimeoutError("FSIS request timed out"),
    b"<html>temporarily unavailable</html>",
])
def test_fsis_access_or_format_failures_remain_source_errors(monkeypatch, tmp_path, failure):
    from ventures.blocks.feeds import core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))

    def fake_urlopen(request, timeout):
        if isinstance(failure, bytes):
            return io.BytesIO(failure)
        raise failure

    monkeypatch.setattr(core.urllib.request, "urlopen", fake_urlopen)
    result = core.sync("fsis_recalls")

    assert result["status"] == "failed_initial"
    assert result["snapshot_available"] is False
    assert result["rows"] == 0
    assert result["alerts"]
    assert "error" in result["alerts"][0].lower() or "alert" in result["alerts"][0].lower()
