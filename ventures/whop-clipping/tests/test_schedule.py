from __future__ import annotations

import sys
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.distributor import distribute_ready, status_report
from scripts.interfaces import Campaign, Clip, Post
from scripts.ledger import Ledger
from scripts.producer import parse_campaign_requirements, produce_ready
from scripts.clipper import write_word_captions
from scripts.variants import assign_segments


def make_campaign(**updates):
    data = dict(id="camp-a", name="Launch", url="https://example.test/campaign", cpm_usd=3,
                budget_left_usd=100, platforms=["youtube_shorts"],
                rules_text="Required tags: #ad #Launch\nDisclosure: Paid partnership\nMentions: @brand\n"
                           "Link: https://example.test\nLength: min 20 max 45\nAllowed edits: captions\n"
                           "Banned content: gambling\nNo editing: false", source_links=[])
    data.update(updates)
    return Campaign(**data)


def test_campaign_requirements_are_saved_as_structured_checklist(tmp_path):
    campaign = make_campaign()
    checklist = parse_campaign_requirements(campaign.rules_text)
    assert checklist["required_tags"] == ["#ad", "#Launch"]
    assert checklist["disclosures"] == ["Paid partnership"]
    assert checklist["mentions"] == ["@brand"]
    assert checklist["links"] == ["https://example.test"]
    assert checklist["min_length_s"] == 20
    assert checklist["max_length_s"] == 45
    assert checklist["allowed_edits"] == ["captions"]
    assert checklist["banned_content"] == ["gambling"]
    assert checklist["no_edit"] is False


def test_any_overlapping_source_time_is_assigned_to_only_one_channel():
    clips = [{"source_id": "source", "start_s": 0, "end_s": 30, "score": 0.9},
             {"source_id": "source", "start_s": 29.5, "end_s": 59.5, "score": 0.8}]
    assigned = assign_segments(clips, ["@first", "@second"])
    assert len(assigned) == 1


def test_ass_caption_word_events_preserve_word_timing_and_channel_colors(tmp_path):
    words = [{"start": 1.00, "end": 1.22, "word": "Launch"},
             {"start": 1.22, "end": 1.50, "word": "today"},
             {"start": 1.50, "end": 1.85, "word": "now"}]
    path = tmp_path / "captions.ass"
    write_word_captions(words, path, {"base": "&H00FFFFFF", "highlight": "&H0000D7FF"})
    rendered = path.read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:01.00,0:00:01.22" in rendered
    assert "Dialogue: 0,0:00:01.22,0:00:01.50" in rendered
    assert "{\\c&H0000D7FF&}Launch" in rendered
    assert "PlayResY: 1920" in rendered


def test_synthetic_clip_caption_timing_stays_within_50ms(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        import pytest
        pytest.skip("ffmpeg is required for the caption timing fixture")
    from scripts.clipper import render_clip
    source = tmp_path / "known-times.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest", "-y", str(source)],
                   check=True)
    words = [{"start": 0.50, "end": 0.78, "word": "known"},
             {"start": 0.80, "end": 1.12, "word": "timing"}]
    output = render_clip(source, tmp_path / "captioned.mp4", start_s=0, end_s=2,
                         caption_words=words, mode="center_crop",
                         caption_style={"base_color": "&H00FFFFFF", "accent_color": "&H0000D7FF"})
    ass_text = output.with_suffix(".ass").read_text(encoding="utf-8")
    rows = re.findall(r"Dialogue: 0,([^,]+),([^,]+),Caption", ass_text)
    def seconds(value):
        hours, minutes, remainder = value.split(":")
        seconds, centis = remainder.split(".")
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100
    assert len(rows) == len(words)
    for (start, end), word in zip(rows, words):
        assert abs(seconds(start) - word["start"]) <= 0.05
        assert abs(seconds(end) - word["end"]) <= 0.05
    assert output.exists()


def test_distributor_uses_nearest_deadline_and_manual_submit_queue(tmp_path, monkeypatch):
    import scripts.distributor as distributor_module
    monkeypatch.setattr(distributor_module, "_ffprobe", lambda path: {"width": 1080, "height": 1920, "audio_loudness_ok": True})
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    channels = ["@first", "@second"]
    ledger = Ledger(tmp_path)
    ledger.set_channel_config("@first", caption="first template", paused=False)
    ledger.set_channel_config("@second", caption="second template", paused=False)
    old_path, fresh_path = tmp_path / "old.mp4", tmp_path / "fresh.mp4"
    old_path.write_bytes(b"master"); fresh_path.write_bytes(b"master")
    old = Clip("old", "camp-a", "src1", 0, 25, str(old_path), "Old", "#ad\n\nPaid partnership", ["#ad"], "", passthrough=True)
    fresh = Clip("fresh", "camp-b", "src2", 30, 55, str(fresh_path), "Fresh", "#ad\n\nPaid partnership", ["#ad"], "", passthrough=True)
    for clip in (old, fresh):
        ledger.record_clip(clip)
        ledger.add_library_clip(clip, checklist={"required_tags": ["#ad"]}, status="ready")
    ledger.record_post(Post("prior", "@first", "youtube_shorts", "v0", "https://youtu.be/v0",
                            (now - timedelta(hours=5, minutes=55)).isoformat()))
    ledger.record_post(Post("prior2", "@second", "youtube_shorts", "v1", "https://youtu.be/v1",
                            (now - timedelta(hours=5, minutes=50)).isoformat()))
    class Uploader:
        def __init__(self): self.calls = []
        def upload(self, clip, *, dry_run=False):
            self.calls.append(clip)
            return Post(clip.id, clip.channel_handle, "youtube_shorts", f"v-{clip.id}",
                        f"https://youtube.test/shorts/{clip.id}", now.isoformat())
    uploader = Uploader()
    config = {"live": True, "channels": channels, "daily_channel_cap": 6, "global_daily_cap": 100,
              "min_spacing_hours": 2, "max_spacing_hours": 6, "approved_campaign_ids": ["camp-a", "camp-b"]}
    result = distribute_ready(config, home=tmp_path, uploader=uploader, now_fn=lambda: now,
                              rng=__import__("random").Random(4), sleep_fn=lambda _: None)
    assert result["uploads"] == 2
    assert uploader.calls[0].id == "old"
    assert uploader.calls[0].channel_handle == "@first"
    assert uploader.calls[1].id == "fresh"
    assert uploader.calls[1].channel_handle == "@second"
    assert ledger.library_item("old")["status"] == "posted"
    queued = ledger.submit_queue()
    assert len(queued) == 2 and queued[0]["url"].endswith("/old")
    page = tmp_path / "submit-queue.html"
    assert page.exists() and "Paid partnership" in page.read_text(encoding="utf-8")
    report = status_report(config, home=tmp_path, now_fn=lambda: now)
    assert report["waiting_for_whop"] == 2
    assert report["channels"]["@first"]["next_deadline"] == (now + timedelta(hours=6)).isoformat()


def test_deadline_risk_alert_and_paused_channel_reporting(tmp_path):
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    ledger = Ledger(tmp_path)
    ledger.set_channel_config("@paused", paused=True, paused_reason="owner pause")
    alerts = []
    config = {"live": True, "channels": ["@paused", "@active"], "daily_channel_cap": 6,
              "approved_campaign_ids": [], "notifications": {}}
    report = status_report(config, home=tmp_path, now_fn=lambda: now, alert_fn=alerts.append)
    assert report["channels"]["@paused"]["paused_reason"] == "owner pause"
    assert any(event["kind"] == "deadline at risk" for event in ledger.events())


def test_producer_fake_scout_stocks_library_and_distributor_uses_fake_submitter(tmp_path, monkeypatch):
    import scripts.producer as producer_module
    import scripts.distributor as distributor_module
    probe = {"width": 1080, "height": 1920, "audio_loudness_ok": True}
    monkeypatch.setattr(producer_module, "_ffprobe", lambda path: probe)
    monkeypatch.setattr(distributor_module, "_ffprobe", lambda path: probe)
    source = tmp_path / "provided.mp4"
    source.write_bytes(b"untouched source bytes")
    campaign = make_campaign(rules_text="Required tags: #ad\nNo editing: true\nLength: min 20 max 45",
                             requires_editing=False)
    clip = Clip("queued", campaign.id, "src-1", 0, 25, str(source), "Title", "#ad", ["#ad"], "",
                passthrough=True)

    class Scout:
        def list_campaigns(self): return [campaign]
    result = produce_ready({"approved_campaign_ids": [campaign.id], "channels": ["@first"]},
                           home=tmp_path / "runtime", scout=Scout(),
                           campaign_clips={campaign.id: [clip]}, target_stock=1)
    assert result["ready"] == 1
    ledger = Ledger(tmp_path / "runtime")
    assert ledger.campaign(campaign.id)["checklist"]["no_edit"] is True
    library_clip = ledger.library_items("ready")[0]
    assert Path(library_clip["clip"]["path"]).read_bytes() == source.read_bytes()

    class Uploader:
        def upload(self, item, *, dry_run=False):
            return Post(item.id, item.channel_handle, "youtube_shorts", "uploaded", "https://youtu.be/uploaded",
                        datetime(2026, 10, 11, 12, tzinfo=timezone.utc).isoformat())
    class Submitter:
        def __init__(self): self.items = []
        def submit(self, campaign, post, *, dry_run=False):
            self.items.append((campaign.id, post.url))
            return "manual-queued"
    submitter = Submitter()
    distribute_ready({"live": True, "channels": ["@first"], "approved_campaign_ids": [campaign.id]},
                     home=tmp_path / "runtime", uploader=Uploader(), submitter=submitter,
                     now_fn=lambda: datetime(2026, 10, 11, 12, tzinfo=timezone.utc),
                     sleep_fn=lambda _: None)
    assert submitter.items == [(campaign.id, "https://youtu.be/uploaded")]
    assert Ledger(tmp_path / "runtime").library_item("queued")["status"] == "posted"


def test_producer_logs_qa_failure_without_marking_clip_ready(tmp_path, monkeypatch):
    import scripts.producer as producer_module
    monkeypatch.setattr(producer_module, "_ffprobe", lambda path: {"width": 1080, "height": 1920, "audio_loudness_ok": True})
    source = tmp_path / "bad.mp4"
    source.write_bytes(b"untouched source bytes")
    campaign = make_campaign(rules_text="Required tags: #ad\nNo editing: true\nLength: min 20 max 45",
                             requires_editing=False)
    clip = Clip("bad", campaign.id, "src", 0, 25, str(source), "Title", "missing tag", [], "",
                passthrough=True)
    result = produce_ready({"approved_campaign_ids": [campaign.id], "channels": ["@first"]},
                           home=tmp_path / "runtime", scout=type("Scout", (), {"list_campaigns": lambda self: [campaign]})(),
                           campaign_clips={campaign.id: [clip]}, target_stock=1)
    ledger = Ledger(tmp_path / "runtime")
    assert result["qa_failures"] == 1 and result["ready"] == 0
    assert ledger.library_item("bad")["status"] == "failed"
    assert any(event["kind"] == "producer_qa_failed" for event in ledger.events())


def test_distributor_respects_two_hour_spacing_and_six_per_day_cap(tmp_path, monkeypatch):
    import scripts.distributor as distributor_module
    monkeypatch.setattr(distributor_module, "_ffprobe", lambda path: {"width": 1080, "height": 1920, "audio_loudness_ok": True})
    now = datetime(2026, 10, 11, 11, 30, tzinfo=timezone.utc)
    ledger = Ledger(tmp_path)
    channels = ["@spacing", "@capped"]
    for channel in channels:
        ledger.set_channel_config(channel)
    ledger.record_post(Post("previous", "@spacing", "youtube_shorts", "p0", "url",
                            (now - timedelta(hours=1, minutes=30)).isoformat()))
    for index in range(6):
        ledger.record_post(Post(f"cap-{index}", "@capped", "youtube_shorts", f"cap-v{index}", "url",
                                now.replace(hour=1, minute=index).isoformat()))
    clip_path = tmp_path / "spacing.mp4"
    clip_path.write_bytes(b"master")
    clip = Clip("spacing-clip", "camp-a", "source-a", 0, 25, str(clip_path),
                "Title", "#ad", ["#ad"], "", passthrough=True)
    ledger.record_clip(clip)
    ledger.add_library_clip(clip, checklist={"required_tags": ["#ad"]})
    waits = []
    current = [now]
    class Uploader:
        def upload(self, item, *, dry_run=False):
            return Post(item.id, item.channel_handle, "youtube_shorts", "new", "https://youtube.test/new", current[0].isoformat())
    config = {"live": True, "channels": channels, "daily_channel_cap": 6}
    ledger.set_next_post_at("@spacing", now - timedelta(minutes=5))
    result = distribute_ready(config, home=tmp_path, uploader=Uploader(), now_fn=lambda: current[0],
                              rng=__import__("random").Random(8), sleep_fn=waits.append)
    assert result["uploads"] == 0  # due time cannot override the 2-hour minimum
    current[0] = now + timedelta(minutes=30)
    result = distribute_ready(config, home=tmp_path, uploader=Uploader(), now_fn=lambda: current[0],
                              rng=__import__("random").Random(8), sleep_fn=waits.append)
    assert result["uploads"] == 1
    assert all(0 <= wait <= 45 * 60 for wait in waits)
    assert ledger.posts_today("@capped", today=now.date().isoformat()) == 6
