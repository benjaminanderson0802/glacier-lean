from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build_from_document
from googleapiclient.http import HttpMockSequence

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.channels import CHANNEL_HANDLES, detect_view_collapse, schedule_slots, snapshot_channel
from scripts.ledger import Ledger


def youtube_service(http):
    discovery_path = (Path(__import__("googleapiclient").__file__).parent /
                      "discovery_cache" / "documents" / "youtube.v3.json")
    return build_from_document(discovery_path.read_text(encoding="utf-8"), http=http)


def response(body):
    return ({"status": "200", "content-type": "application/json"}, json.dumps(body).encode("utf-8"))


def test_ten_configured_handles_and_daily_caps_and_spacing():
    assert len(CHANNEL_HANDLES) == 10
    day = datetime(2026, 10, 11, 8, tzinfo=timezone.utc)
    slots = schedule_slots(day, count=3, daily_channel_cap=3, global_remaining=90,
                           min_spacing_hours=2, jitter_minutes=45, seed=9)
    assert len(slots) == 3
    assert all((right - left).total_seconds() >= 2 * 3600 for left, right in zip(slots, slots[1:]))
    assert schedule_slots(day, count=4, daily_channel_cap=0, global_remaining=90) == []
    assert len(schedule_slots(day, count=9, daily_channel_cap=3, global_remaining=2)) == 2


def test_view_collapse_requires_six_posts_and_compares_7_to_prior_21_days():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    views = [(now - timedelta(days=days), 1000) for days in (1, 2, 3, 4, 5, 6)]
    views += [(now - timedelta(days=days), 1000) for days in (8, 10, 12, 14, 16, 18)]
    assert detect_view_collapse(views, now=now, minimum_posts=6, collapse_ratio=0.2)["collapsed"] is False
    views = [(date, 100) if date >= now - timedelta(days=7) else (date, count)
             for date, count in views]
    result = detect_view_collapse(views, now=now, minimum_posts=6, collapse_ratio=0.2)
    assert result["collapsed"] is True
    assert result["recent_median"] == 100
    assert result["baseline_median"] == 1000


def test_channel_snapshot_reads_uploads_and_pauses_on_collapse(tmp_path):
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    recent = [
        {"id": f"new-{i}", "snippet": {"publishedAt": (now - timedelta(days=i + 1)).isoformat()}}
        for i in range(6)
    ]
    old = [
        {"id": f"old-{i}", "snippet": {"publishedAt": (now - timedelta(days=8 + i)).isoformat()}}
        for i in range(6)
    ]
    items = recent + old
    stats = [{"id": item["id"], "snippet": item["snippet"],
              "statistics": {"viewCount": "100" if item in recent else "1000"}}
             for item in items]
    http = HttpMockSequence([
        response({"items": [{"id": "UC-1", "snippet": {"title": "Frame and Moment"},
                             "contentDetails": {"relatedPlaylists": {"uploads": "UU-1"}}}]}),
        response({"items": [{"contentDetails": {"videoId": item["id"]}, "snippet": item["snippet"]}
                             for item in items], "nextPageToken": ""}),
        response({"items": stats}),
    ])
    ledger = Ledger(tmp_path / "runtime")

    result = snapshot_channel("@frameandmomentdesk", youtube_service(http), ledger,
                              now=now, minimum_posts=6)

    assert result["channel_id"] == "UC-1"
    assert result["views_collapsed"] is True
    assert ledger.is_paused("@frameandmomentdesk", None)
