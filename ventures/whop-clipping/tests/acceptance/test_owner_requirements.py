"""Spec-only acceptance tests for the Whop clipping Producer/Distributor split.

The module entry-point contract exercised here is intentionally small: each
module exposes ``run(config, ..., clock=...)``. Dependencies are injected so
these tests never make network calls, use a browser, or wait on wall time.
"""
from __future__ import annotations

import importlib
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

VENTURE = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(VENTURE))

from scripts.interfaces import Campaign, Clip, Post, Scout, Submitter, Uploader
from scripts.ledger import Ledger


def _module(name):
    try:
        return importlib.import_module(f"scripts.{name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"scripts.{name}":
            pytest.xfail(reason=f"awaiting builder: scripts.{name} does not exist yet")
        raise


def _run(module, **kwargs):
    entry = getattr(module, "run", None)
    assert callable(entry), f"scripts.{module.__name__.rsplit('.', 1)[-1]} must expose run(...)"
    return entry(**kwargs)


class FakeClock:
    def __init__(self, start="2026-10-11T00:00:00+00:00"):
        self.current = datetime.fromisoformat(start)

    def now(self):
        return self.current

    def advance(self, delta):
        self.current += delta


class FakeScout(Scout):
    def __init__(self, campaigns):
        self.campaigns = campaigns
        self.calls = 0

    def list_campaigns(self):
        self.calls += 1
        return list(self.campaigns)


class FakeLibrary:
    """Small in-memory ready-clip library and interaction recorder."""

    def __init__(self, clips=()):
        self.clips = list(clips)
        self.readers = []
        self.writers = []
        self.alerts = []
        self.queue = []
        self.pauses = set()

    def add_ready(self, clip):
        self.writers.append(clip)
        self.clips.append(clip)

    def ready_clips(self, **_filters):
        self.readers.append(dict(_filters))
        return list(self.clips)

    def alert(self, kind, details):
        self.alerts.append((kind, details))

    def enqueue_submission(self, item):
        self.queue.append(item)

    def pause(self, channel, campaign_id, reason):
        self.pauses.add((channel, campaign_id, reason))


class FakeUploader(Uploader):
    def __init__(self, *, failure=None, clock=None):
        self.calls = []
        self.posts = []
        self.failure = failure
        self.clock = clock or _NOW_CLOCK

    def upload(self, clip, *, dry_run=False):
        self.calls.append((clip, dry_run))
        if self.failure:
            raise self.failure
        n = len(self.calls)
        post = Post(clip.id, clip.channel_handle, "youtube_shorts", f"v{n}",
                    f"https://youtube.invalid/shorts/v{n}", self.clock.now().isoformat())
        self.posts.append(post)
        return post


class FakeWhop(Submitter):
    """A local fake endpoint. The expected system queues; it never calls this."""

    def __init__(self, *, status="pending", reason=""):
        self.calls = []
        self.status = status
        self.reason = reason

    def submit(self, campaign, post, *, dry_run=False):
        self.calls.append((campaign, post, dry_run))
        return f"fake-{self.status}:{self.reason}"


_NOW_CLOCK = FakeClock()


def _NOW():
    return _NOW_CLOCK.now()


def _campaign(**changes):
    row = dict(id="camp-1", name="Campaign One", url="https://whop.invalid/c/1",
               cpm_usd=2.0, budget_left_usd=100.0,
               platforms=["youtube_shorts"], rules_text="Required: #ad; disclosure: Paid partnership; 20-58 seconds")
    row.update(changes)
    return Campaign(**row)


def _clip(index, *, start=0, end=30, channel="@alpha", campaign_id="camp-1", hashtags=None,
          path=None, title=None, description=None):
    return Clip(f"clip-{index}", campaign_id, "source-1", start, end,
                path or f"/fake/clip-{index}.mp4", title or f"Clip {index}",
                description if description is not None else "Paid partnership #ad",
                hashtags if hashtags is not None else ["#ad"], channel)


def test_channels_do_not_scout_and_distributor_reads_only_library():
    producer = _module("producer")
    distributor = _module("distributor")
    scout = FakeScout([_campaign()])
    library = FakeLibrary()
    clock = FakeClock()

    _run(producer, config={"live": False}, scout=scout, library=library, clock=clock)
    assert scout.calls > 0, "only Producer is responsible for campaign discovery"

    _run(distributor, config={"live": False}, library=library, uploader=FakeUploader(),
         submitter=FakeWhop(), clock=clock)
    assert library.readers, "Distributor must source work from the central library"
    assert not hasattr(distributor, "scout") or not callable(distributor.scout)


def test_segment_is_not_reused_across_channels_and_shortage_alerts_risk():
    distributor = _module("distributor")
    # 31 seconds overlap in a 60-second candidate: over the 30% conflict limit.
    library = FakeLibrary([_clip(1, start=0, end=60, channel="@alpha"),
                           _clip(2, start=29, end=89, channel="@beta")])
    uploader = FakeUploader()
    result = _run(distributor, config={"live": True, "channels": ["@alpha", "@beta"]},
                  library=library, uploader=uploader, submitter=FakeWhop(), clock=FakeClock())
    assert len(uploader.calls) <= 1, "overlapping segment must never post on two channels"
    assert any("risk" in str(item).lower() and "deadline" in str(item).lower()
               for item in library.alerts) or "deadline_at_risk" in str(result).lower(), \
        "stock shortage must surface a deadline-at-risk alert"


def test_stocked_library_meets_48_hour_cadence_spacing_and_caps():
    distributor = _module("distributor")
    channels = ["@alpha", "@beta"]
    # Distinct source segments avoid overlap conflicts while supplying ample stock.
    clips = [_clip(i, start=i * 70, end=i * 70 + 30, channel="") for i in range(160)]
    library = FakeLibrary(clips)
    clock = FakeClock()
    uploader = FakeUploader(clock=clock)
    result = _run(distributor, config={"live": True, "channels": channels,
                                       "daily_channel_min": 4, "daily_channel_cap": 6,
                                       "min_spacing_hours": 2, "global_daily_cap": 99,
                                       "simulation_hours": 48},
                  library=library, uploader=uploader, submitter=FakeWhop(), clock=clock)
    posts = result.get("posts", uploader.posts)
    by_channel_day = {}
    by_day = {}
    for post in posts:
        stamp = datetime.fromisoformat(post.posted_at)
        day = stamp.date().isoformat()
        by_channel_day.setdefault((post.channel_handle, day), []).append(stamp)
        by_day[day] = by_day.get(day, 0) + 1
    for channel in channels:
        for day_index in (0, 1):
            day = (clock.now().date() + timedelta(days=day_index)).isoformat()
            stamps = by_channel_day.get((channel, day), [])
            assert 4 <= len(stamps) <= 6, f"{channel} posted {len(stamps)} times on {day}"
            assert all((right - left) >= timedelta(hours=2)
                       for left, right in zip(sorted(stamps), sorted(stamps)[1:]))
    assert all(count < 100 for count in by_day.values())
    assert len(uploader.calls) < 100 * 2


@pytest.mark.parametrize("clip, reason", [
    (_clip(1, hashtags=[]), "required tag"),
    (_clip(2, description="No disclosure", hashtags=["#ad"]), "disclosure"),
    (_clip(3, start=0, end=19), "below minimum length"),
    (_clip(4, start=0, end=59), "above maximum length"),
    (_clip(5, path="/fake/not-1080x1920.mp4"), "wrong dimensions"),
])
def test_producer_qa_rejects_clips_that_fail_campaign_rules(clip, reason):
    producer = _module("producer")
    library = FakeLibrary()
    result = _run(producer, config={"live": False}, scout=FakeScout([_campaign()]),
                  library=library, candidates=[clip], clock=FakeClock())
    ready = result.get("ready", library.clips)
    assert clip not in ready, f"clip missing {reason} must not become ready"
    assert clip not in library.writers


def test_word_timed_karaoke_and_channel_colour_pairs_are_stable_and_distinct():
    producer = _module("producer")
    words = [{"word": "Take", "start": 0.10, "end": 0.34},
             {"word": "the", "start": 0.36, "end": 0.48},
             {"word": "shot", "start": 0.50, "end": 0.88}]
    result = _run(producer, config={"live": False}, scout=FakeScout([_campaign()]),
                  library=FakeLibrary(), candidates=[_clip(1)], words=words,
                  channels=["@alpha", "@beta"], clock=FakeClock())
    timed = result["captions"]
    assert len(timed) == len(words)
    for expected, actual in zip(words, timed):
        assert actual["word"].strip() == expected["word"]
        assert abs(actual["start"] - expected["start"]) <= 0.05
        assert abs(actual["end"] - expected["end"]) <= 0.05
        assert actual.get("active_color") or actual.get("highlight_color"), \
            "active karaoke word must carry its highlight color"
    styles = result["channel_styles"]
    first = styles["@alpha"]
    assert first == styles["@alpha"]
    assert first != styles["@beta"]


def test_live_false_is_default_and_never_calls_public_uploader():
    distributor = _module("distributor")
    clip = _clip(1)
    library = FakeLibrary([clip])
    uploader = FakeUploader()
    _run(distributor, config={}, library=library, uploader=uploader,
         submitter=FakeWhop(), clock=FakeClock())
    assert uploader.calls == [] or all(dry for _, dry in uploader.calls)


def test_whop_is_manual_queue_only_and_has_required_submission_details():
    distributor = _module("distributor")
    clip = _clip(1)
    campaign = _campaign()
    library = FakeLibrary([clip])
    whop = FakeWhop()
    _run(distributor, config={"live": True}, library=library, uploader=FakeUploader(),
         submitter=whop, campaigns=[campaign], clock=FakeClock())
    assert whop.calls == [], "Whop Content Rewards submissions must remain manual"
    assert library.queue
    item = library.queue[0]
    assert item["campaign"] == campaign.name or item["campaign_id"] == campaign.id
    assert item["channel"] == clip.channel_handle
    assert "shorts" in item["url"].lower()
    assert item.get("required_caption") is not None
    assert item.get("required_tags") is not None


def test_whop_code_has_no_browser_automation():
    scripts = VENTURE / "scripts"
    browser_modules = {"playwright", "selenium", "pyppeteer", "undetected_chromedriver"}
    for path in scripts.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert not (imported & browser_modules), f"browser automation import in {path.name}"
    assert not (scripts / "whop_login.py").exists(), "Whop login automation is prohibited"


def test_flagged_whop_submission_pauses_only_its_campaign_channel(tmp_path):
    ledger = Ledger(tmp_path)
    campaign = _campaign()
    clip = _clip(1, channel="@alpha")
    ledger.record_clip(clip)
    ledger.record_submission(campaign.id, clip.id, "manual-review-1", "flagged", "flagged disclosure")
    assert ledger.is_paused("@alpha", campaign.id)
    assert not ledger.is_paused("@beta", campaign.id)
    assert not ledger.is_paused("@alpha", "another-campaign")


def test_flagged_campaign_and_youtube_terms_error_pause_and_report():
    distributor = _module("distributor")
    clip = _clip(1)
    library = FakeLibrary([clip])
    uploader = FakeUploader(failure=RuntimeError("YouTube terms of service strike"))
    result = _run(distributor, config={"live": True, "channels": ["@alpha"]},
                  library=library, uploader=uploader,
                  submitter=FakeWhop(status="flagged", reason="flagged"), clock=FakeClock())
    pauses = library.pauses | set(map(tuple, result.get("pauses", [])))
    assert any(row[0] == "@alpha" and (row[1] in (None, "") or row[1] == "camp-1") for row in pauses)
    reports = result.get("paused_channels", [])
    assert "@alpha" in reports or any(row[0] == "@alpha" for row in pauses)


def test_previously_paused_channel_is_excluded_and_reported():
    distributor = _module("distributor")
    library = FakeLibrary([_clip(1, channel="@alpha")])
    library.pauses.add(("@alpha", None, "YouTube strike"))
    uploader = FakeUploader()
    result = _run(distributor, config={"live": True, "channels": ["@alpha"]},
                  library=library, uploader=uploader, submitter=FakeWhop(), clock=FakeClock())
    assert uploader.calls == []
    assert "@alpha" in result.get("paused_channels", [])
