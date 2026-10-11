"""Checks that code-page previews consume the shared feed record shape."""

from __future__ import annotations

import sys
from pathlib import Path


VENTURE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE / "scripts"))

import build_code_pages


class FakeFeeds:
    def __init__(self):
        self.synced = []

    def sync(self, source_id):
        self.synced.append(source_id)
        return {"changed": False, "alerts": []}

    def query(self, source_id):
        if source_id == "cpsc_flagged_tariff_codes":
            return [{"source_url": "https://www.cpsc.gov/eFiling-Document-Library", "fetched_at": "2026-10-10T00:00:00Z",
                     "data": {"tariff_code": "9503000073"}}]
        if source_id == "cpsc_rule_codes":
            return [{"data": {"Citation Code": "1201"}}, {"data": {"Citation Code": "1501"}}]
        raise AssertionError(source_id)


def test_current_objects_flattens_shared_feed_rows(monkeypatch):
    feeds = FakeFeeds()
    monkeypatch.setattr(build_code_pages, "load_blocks", lambda: (None, None, feeds))

    objects = build_code_pages.current_objects()

    assert feeds.synced == ["cpsc_flagged_tariff_codes", "cpsc_rule_codes"]
    assert objects == [{
        "tariff_code": "9503000073",
        "source_url": "https://www.cpsc.gov/eFiling-Document-Library",
        "checked_at": "2026-10-10T00:00:00Z",
        "rule_codes": "1201, 1501",
    }]
