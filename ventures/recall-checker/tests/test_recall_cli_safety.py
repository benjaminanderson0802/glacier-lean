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
