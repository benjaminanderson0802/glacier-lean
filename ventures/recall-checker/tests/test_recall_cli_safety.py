import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


CLI = Path(__file__).parents[1] / "scripts" / "recall.py"
SPEC = importlib.util.spec_from_file_location("recall_checker_cli", CLI)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_nightly_missing_feed_blocks_page_generation_and_returns_alert_code():
    rows = [{"source_id": "cpsc_recalls", "record_id": "1", "fetched_at": "2026-10-10T12:00:00Z", "data": {"RecallNumber": "1", "RecallDate": "2026-10-10", "Title": "Example"}}]
    with tempfile.TemporaryDirectory() as home:
        output = io.StringIO()
        with patch.dict(os.environ, {"GLACIER_HOME": home}), patch.object(sys, "argv", [str(CLI), "nightly", "--skip-sync"]), patch.object(MODULE, "query_recall_feeds", return_value=(rows, ["fsis_recalls"])), contextlib.redirect_stdout(output):
            exit_code = MODULE.main()
        result = json.loads(output.getvalue())
        pages = Path(home) / "ventures" / "recall-checker" / "pages"
    assert exit_code == 2
    assert result["missing_sources"] == ["fsis_recalls"]
    assert result["pages_generated"] == 0
    assert not pages.exists()


def test_nightly_review_packet_generates_at_most_requested_page_limit():
    rows = [{"source_id": "cpsc_recalls", "record_id": str(index), "record_date": f"2026-10-{index:02d}", "fetched_at": "2026-10-11T12:00:00Z", "data": {"RecallNumber": str(index), "RecallDate": "2026-10-10", "Title": f"Example {index}"}} for index in range(1, 76)]
    with tempfile.TemporaryDirectory() as home:
        output = io.StringIO()
        with patch.dict(os.environ, {"GLACIER_HOME": home}), \
             patch.object(sys, "argv", [str(CLI), "nightly", "--skip-sync", "--limit-pages", "50"]), \
             patch.object(MODULE, "query_recall_feeds", return_value=(rows, [])), \
             patch.object(MODULE, "generate_pages", return_value=[f"page-{index}.html" for index in range(50)]) as generate, \
             contextlib.redirect_stdout(output):
            exit_code = MODULE.main()
        result = json.loads(output.getvalue())
    assert exit_code == 0
    assert generate.call_args.kwargs["limit"] == 50
    assert generate.call_args.args[0][0]["record_id"] == "75"
    assert result["pages_generated"] == 50


def test_review_pages_use_record_specific_official_links():
    rows = [
        {"source_id": "fsis_recalls", "record_id": "001-2026", "data": {"field_recall_url": "https://www.fsis.usda.gov/recalls-alerts/example"}},
        {"source_id": "fda_enforcement", "record_id": "F-001-2026", "data": {"_openfda_dataset": "Food", "recall_number": "F-001-2026"}},
        {"source_id": "fda_enforcement", "record_id": "99892", "data": {"_openfda_dataset": "Drug", "event_id": "99892", "recall_number": ""}},
    ]
    prepared = MODULE._page_rows(rows)
    assert prepared[0]["data"]["field_recall_url"] == rows[0]["data"]["field_recall_url"]
    assert prepared[0]["data"]["URL"] == rows[0]["data"]["field_recall_url"]
    assert prepared[1]["data"]["URL"].startswith("https://api.fda.gov/food/enforcement.json?")
    assert "recall_number%3A%22F-001-2026%22" in prepared[1]["data"]["URL"]
    assert "event_id%3A%2299892%22" in prepared[2]["data"]["URL"]
