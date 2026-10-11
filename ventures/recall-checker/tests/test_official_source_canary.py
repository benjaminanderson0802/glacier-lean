import importlib.util
import io
import json
from pathlib import Path
import sys

from ventures.blocks.feeds import query


SCRIPT = Path(__file__).parents[1] / "scripts" / "fsis_canary.py"
sys.path.insert(0, str(SCRIPT.parent))
from fsis_feed import canonical_fsis_records, sync_fsis_feed

SPEC = importlib.util.spec_from_file_location("recall_fsis_canary", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/json"):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_documented_fsis_json_api_canary_recognizes_official_recall_records():
    api_payload = json.dumps([{
        "field_recall_number": "001-2026",
        "field_recall_date": "2026-10-01",
        "field_title": "Example FSIS recall",
    }]).encode()
    rss_payload = b'<rss version="2.0"><channel></channel></rss>'
    responses = iter([Response(api_payload), Response(rss_payload, content_type="application/rss+xml"), Response(rss_payload, content_type="application/rss+xml")])

    def opener(request, timeout):
        assert request.get_header("Referer") is None
        assert "Glacier public-data client" in request.get_header("User-agent")
        return next(responses)

    result = MODULE.probe_official_sources(opener)
    assert result["status"] == "available"
    assert result["complete_snapshot"] is True
    assert result["api"]["identifier_canary_records"] == 1


def test_fsis_403_and_non_fsis_rss_items_keep_coverage_unavailable():
    other_records = b'''<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>FDA item</title><guid>https://www.fda.gov/safety/recalls/example</guid><link>https://tools.cdc.gov/podcasts/download.asp?id=1</link></item>
    </channel></rss>'''
    responses = iter([Response(b"", 403), Response(b"", 403), Response(other_records, content_type="application/rss+xml")])

    result = MODULE.probe_official_sources(lambda request, timeout: next(responses))
    assert result["status"] == "unavailable"
    assert result["complete_snapshot"] is False
    assert result["usable_fsis_rss_records"] == 0
    assert "uncertain" in result["explanation"]


def test_fsis_rss_records_are_only_partial_coverage():
    api_body = b"[]"
    fsis_rss = b'''<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Official FSIS notice</title><guid>https://www.fsis.usda.gov/recalls/example</guid><link>https://www.fsis.usda.gov/recalls/example</link></item>
    </channel></rss>'''
    responses = iter([Response(api_body), Response(fsis_rss, content_type="application/rss+xml"), Response(fsis_rss, content_type="application/rss+xml")])

    result = MODULE.probe_official_sources(lambda request, timeout: next(responses))
    assert result["status"] == "partial"
    assert result["complete_snapshot"] is False
    assert result["usable_fsis_rss_records"] == 2


def test_translated_api_rows_collapse_to_one_english_notice_with_https_link():
    records = [
        {"field_recall_number": "001-2026", "field_recall_date": "2026-10-01", "field_last_modified_date": "2026-10-02", "field_title": "English notice", "field_recall_url": "http://www.fsis.usda.gov/recalls-alerts/example", "langcode": "English"},
        {"field_recall_number": "001-2026", "field_recall_date": "2026-10-01", "field_last_modified_date": "2026-10-02", "field_title": "Aviso en español", "field_recall_url": "http://www.fsis.usda.gov/es/retirada/example", "langcode": "Spanish"},
    ]
    canonical = canonical_fsis_records(records)
    assert len(canonical) == 1
    assert canonical[0]["field_title"] == "English notice"
    assert canonical[0]["field_recall_url"] == "https://www.fsis.usda.gov/recalls-alerts/example"


def test_fsis_sync_promotes_deduplicated_official_snapshot(tmp_path, monkeypatch):
    import ventures.blocks.feeds.core as core

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    records = [
        {"field_recall_number": "001-2026", "field_recall_date": "2026-10-01", "field_last_modified_date": "2026-10-02", "field_title": "English notice", "field_summary": "Example summary", "field_recall_url": "http://www.fsis.usda.gov/recalls-alerts/example", "langcode": "English"},
        {"field_recall_number": "001-2026", "field_recall_date": "2026-10-01", "field_last_modified_date": "2026-10-02", "field_title": "Aviso en español", "field_summary": "Resumen de ejemplo", "field_recall_url": "http://www.fsis.usda.gov/es/retirada/example", "langcode": "Spanish"},
    ]
    monkeypatch.setattr(core, "fetch_source", lambda source_id, config: (records, 2, []))

    result = sync_fsis_feed()
    saved = query("fsis_recalls")
    assert result["status"] == "ok"
    assert result["source_records"] == 2
    assert result["translation_or_duplicate_rows_removed"] == 1
    assert len(saved) == 1
    assert saved[0]["data"]["field_title"] == "English notice"
    assert saved[0]["data"]["field_recall_url"].startswith("https://")
