from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.interfaces import Campaign, Clip, Post
from scripts.ledger import Ledger
from scripts.sources import fetch_source
from scripts.variants import assign_segments, make_variant
from scripts.cycle import run_cycle
from scripts.clipper import candidate_segments, make_clip, score_candidate, transcribe, write_word_captions


def campaign(**overrides):
    values = dict(id="camp-1", name="Campaign", url="https://whop.com/c/1", cpm_usd=2.0,
                  budget_left_usd=20.0, platforms=["youtube_shorts"], rules_text="#ad required",
                  source_links=[], requires_editing=True)
    values.update(overrides)
    return Campaign(**values)


def test_ledger_is_idempotent_and_enforces_pause_overlap_and_daily_caps(tmp_path):
    ledger = Ledger(tmp_path)
    c = campaign()
    clip = Clip("clip1", c.id, "source1", 10, 40, "clip.mp4", "Title", "#ad", ["#ad"], "@frameandmomentdesk")
    post = Post(clip.id, clip.channel_handle, "youtube_shorts", "v1", "https://youtu.be/v1", "2026-10-11T10:00:00+00:00")
    ledger.record_clip(clip)
    assert ledger.record_post(post) is True
    assert ledger.record_post(post) is False
    assert ledger.posts_today(post.channel_handle, today="2026-10-11") == 1
    assert ledger.overlap_used("source1", 20, 45)  # 20s overlap is >30% of the shorter range
    assert not ledger.overlap_used("source1", 41, 50)
    assert ledger.record_submission(c.id, clip.id, "sub-1", "flagged", "flagged by Whop")
    assert ledger.is_paused(post.channel_handle, c.id)
    ledger.pause("@quickreplaydesk", None, "views collapsed")
    assert ledger.is_paused("@quickreplaydesk", c.id)
    assert len(ledger.events()) >= 4


def test_view_collapse_pauses_channel_after_recent_baseline(tmp_path):
    ledger = Ledger(tmp_path)
    for index, views in enumerate((1000, 900, 1100)):
        ledger.record_views("@frameandmomentdesk", f"v{index}", views)
    assert ledger.record_views("@frameandmomentdesk", "v-low", 100) is True
    assert ledger.is_paused("@frameandmomentdesk", "camp-1")


def test_source_fetch_copies_local_media_and_records_provenance(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture-video")
    ledger = Ledger(tmp_path / "runtime")
    result = fetch_source(source.as_uri(), "source1", cache_dir=tmp_path / "cache", ledger=ledger,
                          max_bytes=1024, timeout_s=2)
    assert result.path.read_bytes() == b"fixture-video"
    assert result.cached is False
    assert result.provenance["source_id"] == "source1"
    again = fetch_source(source.as_uri(), "source1", cache_dir=tmp_path / "cache", ledger=ledger,
                         max_bytes=1024, timeout_s=2)
    assert again.cached is True


def test_source_fetch_rejects_size_over_limit(tmp_path):
    source = tmp_path / "oversize.bin"
    source.write_bytes(b"12345")
    with pytest.raises(ValueError, match="size limit"):
        fetch_source(source.as_uri(), "large", cache_dir=tmp_path / "cache", max_bytes=4)


def test_transcribe_uses_a_mocked_faster_whisper_model(monkeypatch, tmp_path):
    class Word:
        start, end, word = 0.0, 0.5, " Hello"

    class Segment:
        start, end, text, words = 0.0, 0.5, "Hello.", [Word()]

    class Info:
        language, duration = "en", 0.5

    class Model:
        def __init__(self, model_size, device, compute_type):
            assert (model_size, device, compute_type) == ("small", "cpu", "int8")

        def transcribe(self, path, **kwargs):
            assert kwargs["word_timestamps"] is True
            return iter([Segment()]), Info()

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model))
    rows, info = transcribe(tmp_path / "sample.mp4")
    assert rows[0]["words"][0]["word"] == "Hello"
    assert info == {"language": "en", "duration": 0.5}


def test_candidate_scoring_uses_hook_complete_sentence_and_campaign_keywords():
    assert score_candidate("Watch this because it changes everything.", 28, ["changes"]) > \
           score_candidate("The thing is different", 28, ["changes"])
    transcript = [
        {"start": 0, "end": 12, "text": "Watch how this works.", "words": []},
        {"start": 12, "end": 25, "text": "This is the campaign moment.", "words": []},
    ]
    candidates = candidate_segments(transcript, "src", "keyword: campaign", min_s=20, max_s=58)
    assert len(candidates) == 1
    assert candidates[0]["score"] > 0.5

    timed = [{"start": 0, "end": 25, "text": "A quiet opening. Watch this campaign moment.",
              "words": [{"start": 0, "end": 0.5, "word": "A"},
                        {"start": 10, "end": 10.5, "word": "Watch"},
                        {"start": 10.5, "end": 11, "word": "this"},
                        {"start": 24, "end": 25, "word": "moment."}]}]
    late_hook = candidate_segments(timed, "src", "", min_s=20, max_s=58)
    assert late_hook[0]["score"] < candidates[0]["score"]


def test_no_edit_campaign_passes_source_through_untouched(tmp_path):
    source = tmp_path / "provided.mp4"
    source.write_bytes(b"provided clip bytes")
    target = make_clip(source, tmp_path / "copied.mp4", {"start_s": 0, "end_s": 1}, requires_editing=False)
    assert target.read_bytes() == source.read_bytes()


def test_channel_caption_styles_are_stable_and_visually_distinct(tmp_path):
    from scripts.variants import channel_style

    first = channel_style("@frameandmomentdesk")
    assert first == channel_style("@frameandmomentdesk")
    second = channel_style("@quickreplaydesk")
    assert first["caption"] != second["caption"]
    captions = tmp_path / "words.ass"
    write_word_captions([{"start": 0, "end": 1, "word": "hello"}], captions, first["caption"])
    assert "Dialogue: 0,0:00:00.00,0:00:01.00" in captions.read_text(encoding="utf-8")


def test_segment_assignment_is_unique_across_channels_and_variant_contains_campaign_tags():
    segments = [
        {"source_id": "s1", "start_s": 1, "end_s": 31, "score": 0.9, "text": "A complete sentence."},
        {"source_id": "s1", "start_s": 35, "end_s": 65, "score": 0.8, "text": "Another sentence."},
    ]
    assignments = assign_segments(segments, ["@frameandmomentdesk", "@quickreplaydesk"], ledger=None)
    assert len(assignments) == 2
    assert assignments[0]["channel_handle"] != assignments[1]["channel_handle"]
    result = make_variant(campaign(rules_text="Required tags: #ad #BrandName. Disclosure: Paid partnership"),
                         segments[0], "@frameandmomentdesk")
    assert "#ad" in result["description"]
    assert "#BrandName" in result["description"]
    assert "Paid partnership" in result["description"]
    assert result["title"]


class FakeScout:
    def __init__(self, campaigns=None):
        self.campaigns = campaigns

    def list_campaigns(self):
        return self.campaigns if self.campaigns is not None else [campaign(source_links=[])]


class FakeUploader:
    def __init__(self):
        self.uploads = []

    def upload(self, clip, *, dry_run=False):
        self.uploads.append((clip, dry_run))
        return Post(clip.id, clip.channel_handle, "youtube_shorts", "fake-v", "https://example.invalid/fake-v", "2026-10-11T10:00:00+00:00")


class FakeSubmitter:
    def __init__(self):
        self.submissions = []

    def submit(self, campaign, post, *, dry_run=False):
        self.submissions.append((campaign.id, post.video_id, dry_run))
        return "fake-submission"


def test_dry_run_cycle_logs_pipeline_without_side_effects(tmp_path):
    config = {
        "live": False,
        "channels": ["@frameandmomentdesk"],
        "daily_channel_cap": 3,
        "global_daily_cap": 100,
        "min_spacing_hours": 2,
        "plugins": {},
        "campaigns": [],
        "approved_campaign_ids": ["camp-1"],
    }
    uploader, submitter = FakeUploader(), FakeSubmitter()
    result = run_cycle(config, home=tmp_path, scout=FakeScout(), uploader=uploader, submitter=submitter,
                       dry_run=True, campaign_clips={"camp-1": []})
    assert result["dry_run"] is True
    assert result["uploads"] == 0
    assert result["submissions"] == 0
    assert uploader.uploads == []
    assert submitter.submissions == []
    assert any(event["kind"] == "cycle_completed" for event in Ledger(tmp_path).events())


def test_unapproved_campaign_and_reached_daily_cap_never_upload(tmp_path):
    config = {"live": True, "channels": ["@frameandmomentdesk"], "approved_campaign_ids": [],
              "daily_channel_cap": 0, "global_daily_cap": 1, "plugins": {}}
    clip = Clip("clip1", "camp-1", "source1", 0, 30, "x.mp4", "Title", "#ad", ["#ad"], "@frameandmomentdesk")
    uploader, submitter = FakeUploader(), FakeSubmitter()
    result = run_cycle(config, home=tmp_path, scout=FakeScout([campaign()]), uploader=uploader,
                       submitter=submitter, dry_run=False, campaign_clips={"camp-1": [clip]})
    assert result["campaigns"] == 0
    assert uploader.uploads == []
    assert submitter.submissions == []

    config["approved_campaign_ids"] = ["camp-1"]
    result = run_cycle(config, home=tmp_path / "capped", scout=FakeScout([campaign()]), uploader=uploader,
                       submitter=submitter, dry_run=False, campaign_clips={"camp-1": [clip]})
    assert result["uploads"] == 0
    assert result["skipped"] == 1
    assert uploader.uploads == []


def test_live_cycle_requires_explicit_config_and_records_side_effects(tmp_path):
    config = {"live": True, "channels": ["@frameandmomentdesk"], "daily_channel_cap": 3,
              "global_daily_cap": 100, "min_spacing_hours": 2, "plugins": {}, "campaigns": []}
    config["approved_campaign_ids"] = ["camp-1"]
    uploader, submitter = FakeUploader(), FakeSubmitter()
    clip = Clip("clip1", "camp-1", "source1", 0, 30, "x.mp4", "Title", "#ad", ["#ad"], "@frameandmomentdesk")
    result = run_cycle(config, home=tmp_path, scout=FakeScout(), uploader=uploader, submitter=submitter,
                       dry_run=False, campaign_clips={"camp-1": [clip]}, sleep_fn=lambda _: None,
                       now_fn=lambda: __import__("datetime").datetime.fromisoformat("2026-10-11T10:00:00+00:00"))
    assert result["uploads"] == 1
    assert result["submissions"] == 1
    assert uploader.uploads[0][1] is False
    assert submitter.submissions[0][2] is False
    assert Ledger(tmp_path).posts_today("@frameandmomentdesk", today="2026-10-11") == 1


def test_dry_run_reservation_can_be_reused_live_on_same_channel(tmp_path):
    config = {"live": True, "channels": ["@frameandmomentdesk"], "approved_campaign_ids": ["camp-1"],
              "daily_channel_cap": 3, "global_daily_cap": 100, "plugins": {}}
    clip = Clip("clip1", "camp-1", "source1", 10, 40, "x.mp4", "Title", "#ad", ["#ad"], "@frameandmomentdesk")
    scout = FakeScout([campaign()])
    uploader, submitter = FakeUploader(), FakeSubmitter()
    run_cycle(config, home=tmp_path, scout=scout, uploader=uploader, submitter=submitter,
              dry_run=True, campaign_clips={"camp-1": [clip]})
    live_result = run_cycle(config, home=tmp_path, scout=scout, uploader=uploader, submitter=submitter,
                            dry_run=False, campaign_clips={"camp-1": [clip]},
                            sleep_fn=lambda _: None)
    assert live_result["uploads"] == 1
    assert live_result["submissions"] == 1


def test_clipper_can_render_lavfi_video_when_ffmpeg_is_available(tmp_path):
    from scripts.clipper import render_clip

    ffmpeg = __import__("shutil").which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is not installed")
    source = tmp_path / "fixture.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest", "-y", str(source)],
                   check=True)
    target = render_clip(source, tmp_path / "out.mp4", start_s=0, end_s=1.5, caption_words=[], mode="center_crop")
    assert target.exists() and target.stat().st_size > 1000
