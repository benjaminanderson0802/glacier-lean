"""Builder regression fixtures. Independent acceptance tests are untouched."""
import csv
import sys
import shutil
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.interfaces import Clip, Campaign, Post
from scripts.ledger import Ledger
from scripts.quality import inspect_media, evaluate_quality, record_review, feedback_summary
from scripts.policy import limits
from scripts.campaigns import allocate_daily_campaign_targets


def words():
    return [{"word": word, "start": i * .45, "end": i * .45 + .43}
            for i, word in enumerate("Watch how this useful example works now.".split())]


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("real ffmpeg and ffprobe required")
    root = tmp_path_factory.mktemp("quality-media")
    def generate(name, video="testsrc2=s=1080x1920:r=12:d=4", audio="sine=f=440:d=4", af="loudnorm=I=-16:TP=-1.5:LRA=11"):
        target = root / (name + ".mp4")
        args = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", video]
        if audio:
            args += ["-f", "lavfi", "-i", audio, "-af", af, "-c:a", "aac"]
        args += ["-t", "4", "-c:v", "libx264", "-threads", "2", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-y", str(target)]
        subprocess.run(args, check=True, capture_output=True)
        return target
    base = generate("base")
    from scripts.clipper import render_clip
    captioned = render_clip(base, root / "captioned.mp4", start_s=0, end_s=4,
                            caption_words=words(), mode="center_crop")
    return root, generate, base, captioned


def clip_for(path, base):
    return Clip("good", "campaign", "source", 0, 4, str(path), "Useful example #ad",
                "Watch this example #ad", ["#ad"], "", caption_words=words(), base_path=str(base))


def test_real_render_passes_and_unchanged_frames_fail_captions(media, tmp_path):
    _, _, base, captioned = media
    clip = clip_for(captioned, base)
    result = evaluate_quality(clip, {"min_length_s": 3, "max_length_s": 5, "required_tags": ["#ad"]}, {}, Ledger(tmp_path))
    assert result["passed"], result
    assert 70 <= result["score"] <= 100
    assert result["signals"]["caption_coverage"] > .8
    bad = evaluate_quality(replace(clip, path=str(base)), {}, {}, Ledger(tmp_path))
    assert any("captions" in reason for reason in bad["reasons"])


@pytest.mark.parametrize("name,video,audio,af,reason", [
    ("black", "color=black:s=1080x1920:r=12:d=4", "sine=f=440:d=4", "loudnorm=I=-16", "black"),
    ("frozen", "color=red:s=1080x1920:r=12:d=4", "sine=f=440:d=4", "loudnorm=I=-16", "frozen"),
    ("mute", "testsrc2=s=1080x1920:r=12:d=4", None, "anull", "audio"),
    ("quiet", "testsrc2=s=1080x1920:r=12:d=4", "sine=f=440:d=4", "volume=0.01", "loudness"),
    ("silence", "testsrc2=s=1080x1920:r=12:d=4", "sine=f=440:d=4", "volume=0:enable='lt(t,2.5)'", "silence"),
    ("clipped", "testsrc2=s=1080x1920:r=12:d=4", "aevalsrc=sgn(sin(440*2*PI*t)):d=4", "anull", "clipping"),
    ("small", "testsrc2=s=320x240:r=12:d=4", "sine=f=440:d=4", "loudnorm=I=-16", "1080x1920"),
])
def test_generated_defects_fail(media, tmp_path, name, video, audio, af, reason):
    _, generate, base, _ = media
    path = generate(name, video, audio, af)
    result = evaluate_quality(clip_for(path, base), {}, {}, Ledger(tmp_path))
    assert not result["passed"]
    assert any(reason in item for item in result["reasons"]), result


def test_metadata_length_brand_banned_and_threshold(media, tmp_path):
    _, _, base, captioned = media
    clip = clip_for(captioned, base)
    clip.caption_words = [{**word, "word": "Acmee" if i == 0 else word["word"]} for i, word in enumerate(words())]
    result = evaluate_quality(clip, {"min_length_s": 5, "required_tags": ["#missing"],
                              "brand_spelling": "Acme", "banned_content": ["example"]},
                              {"min_quality": 100}, Ledger(tmp_path))
    for reason in ("length", "tags", "spelling", "banned", "quality score"):
        assert any(reason in item for item in result["reasons"]), result


def test_duplicates_across_campaigns_and_overlap(media, tmp_path):
    _, _, base, captioned = media
    ledger = Ledger(tmp_path)
    clip = clip_for(captioned, base)
    result = evaluate_quality(clip, {}, {}, ledger)
    clip.quality = result
    ledger.record_clip(clip)
    ledger.add_library_clip(clip, checklist={})
    duplicate = replace(clip, id="other", campaign_id="other-campaign", source_id="other-source")
    result = evaluate_quality(duplicate, {}, {}, ledger)
    assert any("near-duplicate" in item for item in result["reasons"])
    overlap = replace(duplicate, source_id="source", start_s=3, end_s=7)
    assert any("overlap" in item for item in evaluate_quality(overlap, {}, {}, ledger)["reasons"])


def test_review_feedback_and_capped_allocation(media, tmp_path):
    _, _, base, captioned = media
    ledger = Ledger(tmp_path)
    clip = clip_for(captioned, base)
    clip.title = "<script>bad()</script>"
    ledger.record_clip(clip)
    review = record_review(ledger, clip, {"score": 60, "reasons": ["too quiet"]}, "rejected")
    text = review.read_text()
    assert "&lt;script&gt;" in text and "too quiet" in text and "data:image/jpeg;base64," in text
    with (tmp_path / "whop_results.csv").open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(["clip_id", "status", "reason"])
        writer.writerow([clip.id, "rejected", "low effort"])
    summary = feedback_summary(ledger)
    assert summary["campaign"]["factor"] < 1
    assert "low effort" in summary["campaign"]["reasons"]
    campaigns = [Campaign(key, key, "", 1, 100, [], "") for key in ("campaign", "b")]
    allocation = allocate_daily_campaign_targets(campaigns, 80, capacities={"campaign": 2, "b": 50}, feedback=summary)
    assert allocation == {"campaign": 2, "b": 50}
    allocation = allocate_daily_campaign_targets(campaigns, 80, feedback=summary)
    assert allocation["campaign"] < allocation["b"]


def test_policy_hold_and_atomic_pacific_quota(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from scripts.distributor import distribute_ready
    assert limits({}) == {"daily_target": 80, "per_channel_daily": 8, "min_gap_minutes": 150, "interval_minutes": 180, "upload_cap": 85}
    (tmp_path / "HOLD").touch()
    assert distribute_ready({"live": True}, home=tmp_path)["held"]
    ledger = Ledger(tmp_path)
    now = datetime(2026, 10, 11, 23, tzinfo=timezone.utc)
    def reserve(index):
        return ledger.reserve_upload_quota(str(index), "@channel", now, cap=85)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(100))) == 85
    assert not ledger.reserve_upload_quota("again", "@channel", now + timedelta(hours=7), cap=85)
    assert ledger.reserve_upload_quota("tomorrow", "@channel", now + timedelta(hours=8), cap=85)


def test_real_producer_and_variant_recheck(media, tmp_path, monkeypatch):
    from scripts.producer import produce_ready
    from scripts.distributor import distribute_ready
    _, _, base, captioned = media
    campaign = Campaign("campaign", "Example", "", 1, 100, ["youtube_shorts"], "Length: min 3 max 5\nRequired tags: #ad")
    scout = type("Scout", (), {"list_campaigns": lambda self: [campaign]})()
    clip = clip_for(base, base)
    config = {"live": True, "channels": ["@one"], "approved_campaign_ids": [campaign.id],
              "campaigns_dir": str(tmp_path / "empty"), "daily_target": 80}
    output = produce_ready(config, home=tmp_path, scout=scout, campaign_clips={campaign.id: [clip]})
    assert output["produced"] == 1, output
    calls = []
    now = datetime.now(timezone.utc)
    class Uploader:
        def upload(self, variant, **kwargs):
            calls.append(variant)
            return Post(variant.id, variant.channel_handle, "youtube_shorts", "video", "https://example.test/video", now.isoformat())
    result = distribute_ready(config, home=tmp_path, uploader=Uploader(), now_fn=lambda: now)
    assert result["uploads"] == 1, result
    assert calls[0].quality["score"] >= 70
    page = next((tmp_path / "review").glob("*.html"))
    assert "posted" in page.read_text()
    # A changed/corrupt variant must fail even with a previously passing score.
    fresh = replace(clip, id="corrupt", source_id="fresh-source", quality={"score": 99})
    fresh.path = str(tmp_path / "broken.mp4")
    Path(fresh.path).write_bytes(b"broken media")
    fresh.base_path = fresh.path
    ledger = Ledger(tmp_path)
    ledger.record_clip(fresh)
    ledger.add_library_clip(fresh, checklist={})
    result = distribute_ready(config, home=tmp_path, uploader=Uploader(), now_fn=lambda: now + timedelta(hours=3))
    assert result["uploads"] == 0
    assert ledger.library_item("corrupt")["status"] == "failed"
    assert "rejected" in page.read_text()


def test_hourly_dispatch_hits_80_evenly_and_uses_highest_scores(tmp_path, monkeypatch):
    import scripts.distributor as module
    monkeypatch.setattr(module, "_channel_variant", lambda clip, *args: clip)
    monkeypatch.setattr(module, "evaluate_quality", lambda clip, *args: {"score": clip.quality["score"], "reasons": []})
    monkeypatch.setattr(module, "record_review", lambda *args: None)
    channels = ["@channel" + str(i) for i in range(10)]
    config = {"live": True, "channels": channels}
    ledger = Ledger(tmp_path)
    path = tmp_path / "media.mp4"
    path.touch()
    for i in range(80):
        clip = Clip(str(i), "camp", str(i), 0, 4, str(path), "title", "description", [], "", passthrough=True,
                    quality={"score": 70 + i % 30})
        ledger.record_clip(clip)
        ledger.add_library_clip(clip, checklist={})
    now = datetime(2026, 10, 11, 7, tzinfo=timezone.utc)
    calls = []
    class Uploader:
        def upload(self, clip, **kwargs):
            calls.append((clip.quality["score"], clip.channel_handle, now))
            return Post(clip.id, clip.channel_handle, "youtube_shorts", "v"+clip.id, "url", now.isoformat())
    for _ in range(24):
        module.distribute_ready(config, home=tmp_path, uploader=Uploader(), now_fn=lambda: now)
        now += timedelta(hours=1)
    assert len(calls) == 80
    assert calls[0][0] == 99
    for channel in channels:
        times = [at for _, handle, at in calls if handle == channel]
        assert len(times) == 8
        assert all(b-a == timedelta(hours=3) for a, b in zip(times, times[1:]))


def test_missing_hook_and_sparse_speech_are_scored_locally(media, tmp_path, monkeypatch):
    import scripts.quality as module
    _, _, base, captioned = media
    original = module.inspect_media(captioned)
    signals = {**original, "motion": 0, "hook_motion": 0}
    monkeypatch.setattr(module, "inspect_media", lambda _: signals)
    monkeypatch.setattr(module, "caption_evidence", lambda _: 1)
    clip = clip_for(captioned, base)
    clip.caption_words = [{"word": token, "start": 2.5+i*.2, "end": 2.65+i*.2} for i, token in enumerate(["late", "speech", "fragment"])]
    result = module.evaluate_quality(clip, {}, {}, Ledger(tmp_path))
    assert any("hook" in reason for reason in result["reasons"])
    assert result["score"] < 70
    assert result["signals"]["components"]["completeness_of_thought"] < 15


def test_quota_stop_preserves_stock_and_status_explains_feedback(tmp_path):
    from scripts.distributor import distribute_ready, status_report
    ledger = Ledger(tmp_path)
    now = datetime(2026, 10, 11, 20, tzinfo=timezone.utc)
    for index in range(85):
        assert ledger.reserve_upload_quota(str(index), "@one", now)
    clip = Clip("ready", "camp", "source", 0, 4, "missing.mp4", "title", "description", [], "")
    ledger.record_clip(clip)
    ledger.add_library_clip(clip, checklist={})
    uploader = type("Uploader", (), {"upload": lambda *args, **kwargs: pytest.fail("quota stop must not upload")})()
    result = distribute_ready({"live": True, "channels": ["@one"]}, home=tmp_path, uploader=uploader, now_fn=lambda: now)
    assert result["quota_stopped"]
    assert ledger.library_item("ready")["status"] == "ready"
    (tmp_path / "whop_results.csv").write_text("clip_id,status,reason\nready,rejected,poor hook\n")
    status = status_report({"channels": ["@one"]}, home=tmp_path, now_fn=lambda: now)
    assert status["upload_quota_remaining"] == 0
    assert status["whop_feedback"]["camp"]["reasons"] == ["poor hook"]


def test_minimum_gap_is_configurable_and_never_overridden_by_deadline(tmp_path):
    from scripts.distributor import _channel_assignment
    ledger = Ledger(tmp_path)
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    ledger.record_post(Post("prior", "@one", "youtube_shorts", "video", "url", now.isoformat()))
    ledger.set_next_post_at("@one", now)
    assert not _channel_assignment(ledger, ["@one"], now + timedelta(minutes=149), {})
    assert _channel_assignment(ledger, ["@one"], now + timedelta(minutes=150), {})
    assert not _channel_assignment(ledger, ["@one"], now + timedelta(minutes=170), {"min_gap_minutes": 180})


def test_source_capacity_is_planned_before_render_and_capped(tmp_path, monkeypatch):
    import scripts.producer as module
    campaign = Campaign("camp", "Example", "", 1, 100, ["youtube_shorts"], "Length: min 20 max 40",
                        source_links=["https://example.test/source"])
    source_path = tmp_path / "source.mp4"
    source_path.touch()
    source = type("Source", (), {"path": source_path, "url": "https://example.test/source", "provenance": {"sha256": "a"*64}})()
    monkeypatch.setattr(module, "fetch_source", lambda *args, **kwargs: source)
    monkeypatch.setattr(module, "transcribe", lambda *args, **kwargs: ([], {}))
    monkeypatch.setattr(module, "candidate_segments", lambda *args, **kwargs: [
        {"source_id": "a"*20, "start_s": 0, "end_s": 25, "text": "first", "words": []},
        {"source_id": "a"*20, "start_s": 20, "end_s": 45, "text": "overlap", "words": []},
        {"source_id": "a"*20, "start_s": 50, "end_s": 75, "text": "second", "words": []}])
    monkeypatch.setattr(module, "make_clip", lambda *args, **kwargs: pytest.fail("planning must not render"))
    plans = list(module._iter_prepared_clips(campaign, {}, Ledger(tmp_path), tmp_path, plan_only=True))
    assert len(plans) == 2
    assert not any(Path(plan[0].path).exists() for plan in plans)
    assert allocate_daily_campaign_targets([campaign], 80, capacities={"camp": len(plans)}) == {"camp": 2}


def test_real_source_plan_render_stock_path(media, tmp_path, monkeypatch):
    import scripts.producer as module
    _, _, base, _ = media
    campaign = Campaign("camp", "Example", "", 1, 100, ["youtube_shorts"], "Length: min 3 max 5\nRequired tags: #ad",
                        source_links=["https://example.test/source"])
    source = type("Source", (), {"path": base, "url": "https://example.test/source", "provenance": {"sha256": "b"*64}})()
    monkeypatch.setattr(module, "fetch_source", lambda *args, **kwargs: source)
    monkeypatch.setattr(module, "transcribe", lambda *args, **kwargs: ([], {}))
    monkeypatch.setattr(module, "candidate_segments", lambda *args, **kwargs: [
        {"source_id": "b"*20, "start_s": 0, "end_s": 4, "text": "Watch how this useful example works now.", "words": words()}])
    scout = type("Scout", (), {"list_campaigns": lambda self: [campaign]})()
    result = module.produce_ready({"channels": ["@one"], "approved_campaign_ids": ["camp"],
                                   "campaigns_dir": str(tmp_path / "empty")}, home=tmp_path, scout=scout)
    assert result["campaign_targets"] == {"camp": 1}
    assert result["produced"] == 1, result
    stored = Ledger(tmp_path).library_items()[0]["clip"]
    assert stored["quality"]["passed"]
    assert Path(stored["base_path"]).exists()
    assert Path(stored["path"]).read_bytes() != Path(stored["base_path"]).read_bytes()
