"""Acceptance coverage for multi-campaign production and source handling.

These checks use local fixtures and injected fetchers. The opt-in network smoke
test is deliberately separate so routine suites never download campaign media.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))


@pytest.fixture(autouse=True)
def isolate_campaign_registry(tmp_path, monkeypatch):
    import scripts.producer as producer
    campaigns_dir = tmp_path / "fixture-campaigns"
    campaigns_dir.mkdir()
    monkeypatch.setattr(producer, "DEFAULT_CAMPAIGNS_DIR", campaigns_dir)


def campaign_files(root: Path, campaign_id="camp-a", **summary):
    folder = root / "campaigns" / campaign_id
    folder.mkdir(parents=True)
    (folder / "summary.json").write_text(json.dumps({
        "id": campaign_id, "name": campaign_id, "url": f"https://example.test/{campaign_id}",
        "cpm_usd": 5, "budget_left_usd": 100, "platforms": ["youtube_shorts"],
        "eligible_for_new_youtube_shorts_channels": True, **summary,
    }), encoding="utf-8")
    (folder / "rules.txt").write_text("Length: min 20 max 45\nRequired tags: #ad\n", encoding="utf-8")
    (folder / "sources.txt").write_text("https://example.test/video.mp4\n", encoding="utf-8")
    return folder


def test_campaign_registry_loads_repo_and_clip_home_overrides(tmp_path):
    from scripts.campaigns import load_campaign_registry

    repo = tmp_path / "repo"
    home = tmp_path / "home"
    campaign_files(repo, cpm_usd=2)
    override = campaign_files(home, cpm_usd=9)
    (override / "rules.txt").write_text("Required tags: #override\n", encoding="utf-8")
    rows = load_campaign_registry(repo, home)
    assert len(rows) == 1
    assert rows[0].cpm_usd == 9
    assert rows[0].rules_text == "Required tags: #override\n"
    assert rows[0].source_links == [{"url": "https://example.test/video.mp4"}]


def test_partial_private_brief_only_overrides_present_files(tmp_path):
    from scripts.campaigns import load_campaign_registry
    repo, home = tmp_path / "repo", tmp_path / "home"
    campaign_files(repo, cpm_usd=2)
    private = home / "campaigns" / "camp-a"
    private.mkdir(parents=True)
    (private / "summary.json").write_text(json.dumps({"id": "camp-a", "cpm_usd": 8}), encoding="utf-8")
    campaign = load_campaign_registry(repo, home)[0]
    assert campaign.cpm_usd == 8
    assert campaign.rules_text.startswith("Length:")
    assert campaign.source_links == [{"url": "https://example.test/video.mp4"}]


def test_legacy_clip_home_rule_and_source_files_override_registry(tmp_path, monkeypatch):
    from scripts.campaigns import load_campaign_registry
    from scripts.producer import _campaign_sources, produce_ready
    from scripts.interfaces import Campaign, Clip
    import scripts.producer as producer
    repo, home = tmp_path / "repo", tmp_path / "home"
    campaign_files(repo)
    (home / "campaign_rules").mkdir(parents=True)
    (home / "campaign_rules" / "camp-a.txt").write_text("Required tags: #private\n", encoding="utf-8")
    (home / "campaign_sources").mkdir(parents=True)
    (home / "campaign_sources" / "camp-a.txt").write_text("https://private.test/video.mp4\n", encoding="utf-8")
    campaign = load_campaign_registry(repo, home)[0]
    assert _campaign_sources(campaign, home)[0]["url"] == "https://private.test/video.mp4"
    class Scout:
        joined_campaign_ids = [campaign.id]
        def list_campaigns(self): return [campaign]
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture")
    clip = Clip("clip", "camp-a", "source", 0, 25, str(media), "Title #private", "", ["#private"], "", passthrough=True)
    monkeypatch.setattr(producer, "_ffprobe",
                        lambda _: {"width": 1080, "height": 1920, "audio_loudness_ok": True})
    result = produce_ready({"campaign_registry": str(repo), "channels": ["@one"], "daily_target_clips": 1},
                           home=home, scout=Scout(), campaign_clips={"camp-a": [clip]})
    assert result["qa_rules_enforced"]["camp-a"]["required_tags"] == ["#private"]


def test_producer_marks_ffprobe_error_as_clip_qa_failure_and_continues(tmp_path, monkeypatch):
    import subprocess
    import scripts.producer as producer
    from scripts.interfaces import Campaign, Clip

    campaign = Campaign("camp", "Camp", "", 1, None, ["youtube_shorts"], "Required tags: #ad")
    bad_path, good_path = tmp_path / "bad.mp4", tmp_path / "good.mp4"
    bad_path.write_bytes(b"bad fixture")
    good_path.write_bytes(b"good fixture")
    bad = Clip("bad", campaign.id, "source", 0, 25, str(bad_path), "Title #ad", "", ["#ad"], "", passthrough=True)
    good = Clip("good", campaign.id, "source", 30, 55, str(good_path), "Title #ad", "", ["#ad"], "", passthrough=True)

    def ffprobe(path):
        if path == str(bad_path):
            raise subprocess.CalledProcessError(1, ["ffprobe", path], stderr="invalid media")
        return {"width": 1080, "height": 1920, "audio_loudness_ok": True}

    monkeypatch.setattr(producer, "_ffprobe", ffprobe)

    class Scout:
        joined_campaign_ids = [campaign.id]
        def list_campaigns(self): return [campaign]

    result = producer.produce_ready({"channels": ["@one"], "daily_target_clips": 1},
                                    home=tmp_path / "home", scout=Scout(),
                                    campaign_clips={campaign.id: [bad, good]}, target_stock=2)

    ledger = __import__("scripts.ledger", fromlist=["Ledger"]).Ledger(tmp_path / "home")
    assert result["qa_failures"] == 1
    assert ledger.library_item("bad")["status"] == "failed"
    assert "media probe failed" in ledger.library_item("bad")["qa_failures"][0]
    assert ledger.library_item("good")["status"] == "ready"


def test_campaign_ineligible_for_new_channels_is_logged_and_skipped(tmp_path):
    from scripts.campaigns import load_campaign_registry
    from scripts.producer import produce_ready

    repo = tmp_path / "repo"
    campaign_files(repo, eligible_for_new_youtube_shorts_channels=False)
    campaign = load_campaign_registry(repo, tmp_path / "home")[0]
    class Scout:
        joined_campaign_ids = [campaign.id]
        def list_campaigns(self): return [campaign]
    result = produce_ready({"channels": ["@one"], "campaign_registry": str(repo)},
                          home=tmp_path / "home", scout=Scout(), campaign_clips={campaign.id: []})
    assert result["campaigns"] == 0
    assert any(row["kind"] == "campaign_ineligible" for row in result["errors"])


def test_conditional_campaign_requires_explicit_allow_list_and_status_shows_summary_actions(tmp_path):
    from scripts.campaigns import load_campaign_registry
    from scripts.distributor import status_report
    from scripts.producer import produce_ready

    repo = tmp_path / "repo"
    campaign_files(repo, eligible_for_new_youtube_shorts_channels="Conditional",
                   needs_owner_action=["Provide channel demographics"])
    campaign = load_campaign_registry(repo, tmp_path / "home")[0]

    class Scout:
        joined_campaign_ids = [campaign.id]
        def list_campaigns(self): return []

    config = {"channels": ["@one"], "campaigns_dir": str(repo / "campaigns")}
    blocked = produce_ready(config, home=tmp_path / "blocked", scout=Scout(),
                            campaign_clips={campaign.id: []}, target_stock=0)
    assert blocked["campaigns"] == 0

    allowed = produce_ready({**config, "allow_conditional_campaign_ids": [campaign.id]},
                            home=tmp_path / "allowed", scout=Scout(),
                            campaign_clips={campaign.id: []}, target_stock=0)
    assert allowed["campaigns"] == 1
    status = status_report(config, home=tmp_path / "fresh")
    assert status["owner_actions"][campaign.id] == [
        {"requirement": "Provide channel demographics", "reason": "campaign brief requires owner action"}
    ]


def test_campaign_daily_targets_weight_cpm_and_budget_but_give_each_one(tmp_path):
    from scripts.campaigns import allocate_daily_campaign_targets
    rows = [
        {"id": "large", "cpm_usd": 10, "budget_left_usd": 1000},
        {"id": "small", "cpm_usd": 5, "budget_left_usd": 500},
        {"id": "third", "cpm_usd": 2, "budget_left_usd": 200},
    ]
    allocations = allocate_daily_campaign_targets(rows, total=40)
    assert sum(allocations.values()) == 40
    assert all(allocations[key] >= 1 for key in ("large", "small", "third"))
    assert allocations["large"] > allocations["small"] > allocations["third"]


def test_source_cache_enforces_disk_budget_with_lru_eviction(tmp_path):
    from scripts.sources import enforce_source_budget
    cache = tmp_path / "sources"
    cache.mkdir()
    old = cache / "old.mp4"
    new = cache / "new.mp4"
    old.write_bytes(b"a" * 6)
    new.write_bytes(b"b" * 6)
    os.utime(old, (10, 10))
    os.utime(new, (20, 20))
    removed = enforce_source_budget(cache, max_source_gb=0.00000001, protected={new})
    assert removed == [old]
    assert not old.exists() and new.exists()


def test_google_drive_folder_uses_gdown_folder_and_extracts_results(tmp_path, monkeypatch):
    from scripts.sources import _fetch_google_drive
    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        output = Path(args[args.index("-O") + 1])
        output.mkdir(parents=True, exist_ok=True)
        (output / "source.mp4").write_bytes(b"drive-video")
        return type("Completed", (), {"returncode": 0})()
    monkeypatch.setattr("scripts.sources.subprocess.run", fake_run)
    result = _fetch_google_drive("https://drive.google.com/drive/folders/abc", tmp_path / "out", 100, 30)
    assert "--folder" in calls[0]
    assert result.read_bytes() == b"drive-video"


def test_google_drive_file_uses_gdown_public_file_adapter(tmp_path, monkeypatch):
    from scripts.sources import _fetch_google_drive
    output = tmp_path / "public.mp4"
    def download(url, target, **kwargs):
        assert url == "https://drive.google.com/file/d/abc/view"
        Path(target).write_bytes(b"drive-file")
        return str(target)
    monkeypatch.setattr("gdown.download", download)
    assert _fetch_google_drive("https://drive.google.com/file/d/abc/view", output, 100, 30).read_bytes() == b"drive-file"


def test_dropbox_folder_downloads_zip_extracts_safely(tmp_path, monkeypatch):
    from scripts.sources import _fetch_dropbox
    archive = tmp_path / "shared.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("folder/video.mp4", b"dropbox-video")
    seen = []
    def download(url, target, max_bytes, timeout_s):
        seen.append(url)
        Path(target).write_bytes(archive.read_bytes())
    monkeypatch.setattr("scripts.sources._download_direct", download)
    result = _fetch_dropbox("https://www.dropbox.com/sh/abc?dl=0", tmp_path / "out", 1000, 30)
    assert "dl=1" in seen[0]
    assert result.read_bytes() == b"dropbox-video"


def test_dropbox_shared_file_forces_download_and_caches_bytes(tmp_path, monkeypatch):
    from scripts.sources import _fetch_dropbox
    seen = []
    def download(url, target, max_bytes, timeout_s):
        seen.append(url)
        Path(target).write_bytes(b"dropbox-file")
    monkeypatch.setattr("scripts.sources._download_direct", download)
    result = _fetch_dropbox("https://www.dropbox.com/s/abc/clip.mp4?dl=0", tmp_path / "clip.mp4", 100, 30)
    assert "dl=1" in seen[0]
    assert result.read_bytes() == b"dropbox-file"


def test_wetransfer_metadata_records_expiry_and_cache_path(tmp_path, monkeypatch):
    from scripts.sources import fetch_source
    import scripts.sources as sources
    def fake_wetransfer(url, target, max_bytes, timeout_s):
        Path(target).write_bytes(b"cached-transfer")
        return {"expires_at": "2026-10-12T00:00:00Z", "download_url": "https://download.test/file"}
    monkeypatch.setattr(sources, "_fetch_wetransfer", fake_wetransfer)
    result = fetch_source("https://wetransfer.com/downloads/token", "source", cache_dir=tmp_path,
                          max_bytes=100, timeout_s=10)
    assert result.path.read_bytes() == b"cached-transfer"
    assert result.provenance["expires_at"] == "2026-10-12T00:00:00Z"
    assert result.provenance["cached"] is False
    cached = fetch_source("https://wetransfer.com/downloads/token", "source", cache_dir=tmp_path,
                          max_bytes=100, timeout_s=10)
    assert cached.provenance["expires_at"] == "2026-10-12T00:00:00Z"
    assert cached.provenance["cached"] is True


def test_producer_stocks_each_qa_passing_clip_before_rendering_next(tmp_path, monkeypatch):
    from scripts.interfaces import Campaign, Clip
    import scripts.producer as producer
    order = []
    original = producer.make_clip
    def render(*args, **kwargs):
        order.append("render")
        return original(*args, **kwargs)
    # Injected clip rows model individually rendered candidates without ffmpeg.
    campaign = Campaign("camp", "Camp", "https://example.test", 1, 20, ["youtube_shorts"],
                        "Length: min 20 max 45\nRequired tags: #ad")
    paths = []
    clips = []
    for index in range(3):
        path = tmp_path / f"{index}.mp4"
        path.write_bytes(b"fixture")
        paths.append(path)
        clips.append(Clip(str(index), "camp", "source", index * 60, index * 60 + 25,
                          str(path), "Title #ad", "Disclosure", ["#ad"], "", passthrough=True))
    monkeypatch.setattr(producer, "_ffprobe", lambda _: {"width": 1080, "height": 1920, "audio_loudness_ok": True})
    class Scout:
        joined_campaign_ids = ["camp"]
        def list_campaigns(self): return [campaign]
    ledger = __import__("scripts.ledger", fromlist=["Ledger"]).Ledger(tmp_path / "home")
    def clips_iter():
        yield clips[0]
        assert len(ledger.library_items("ready")) == 1
        yield clips[1]
        assert len(ledger.library_items("ready")) == 2
        yield clips[2]
    result = producer.produce_ready({"channels": ["@one"], "approved_campaign_ids": ["camp"],
                                     "daily_target_clips": 2},
                                    home=tmp_path / "home", scout=Scout(),
                                    campaign_clips={"camp": clips_iter()}, target_stock=2)
    assert result["produced"] == 2
    assert len(__import__("scripts.ledger", fromlist=["Ledger"]).Ledger(tmp_path / "home").library_items("ready")) == 2


def test_rules_surface_unautomatable_steps_and_preapproval_blocks_public_upload(tmp_path):
    from scripts.producer import parse_campaign_requirements
    from scripts.distributor import distribute_ready
    from scripts.ledger import Ledger
    from scripts.interfaces import Campaign, Clip
    rules = "Length: min 20 max 45\nLink in bio required\nDemographics screenshots required\nDraft pre-approval required"
    checklist = parse_campaign_requirements(rules)
    assert {row["requirement"] for row in checklist["owner_actions"]} >= {
        "link_in_bio", "demographics_screenshots", "draft_preapproval"}
    assert checklist["draft_preapproval"] is True
    home = tmp_path / "home"
    media = home / "library" / "clip.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"fixture")
    clip = Clip("clip", "camp", "source", 0, 25, str(media), "Title", "", [], "", passthrough=True)
    ledger = Ledger(home)
    ledger.record_clip(clip)
    ledger.record_campaign(Campaign("camp", "Camp", "", 1, 1, ["youtube_shorts"], rules))
    ledger.save_campaign_checklist("camp", checklist)
    ledger.add_library_clip(clip, checklist=checklist, status="ready")
    class Uploader:
        calls = 0
        def upload(self, *_a, **_k): self.calls += 1
    uploader = Uploader()
    result = distribute_ready({"live": True, "channels": ["@one"], "approved_campaign_ids": ["camp"]},
                              home=home, uploader=uploader)
    assert uploader.calls == 0
    assert result["uploads"] == 0
    assert result["owner_actions"]["camp"]
    from scripts.distributor import status_report
    assert status_report({"channels": ["@one"]}, home=home)["owner_actions"]["camp"]


def test_distributor_never_posts_overlapping_source_moments_to_two_channels(tmp_path, monkeypatch):
    from scripts.distributor import distribute_ready
    from scripts.interfaces import Campaign, Clip
    from scripts.ledger import Ledger
    import scripts.distributor as distributor
    monkeypatch.setattr(distributor, "_ffprobe", lambda _: {"width": 1080, "height": 1920,
                                                              "audio_loudness_ok": True})
    ledger = Ledger(tmp_path)
    for index, (start, end) in enumerate(((0, 30), (10, 40))):
        path = tmp_path / f"{index}.mp4"
        path.write_bytes(b"fixture")
        clip = Clip(str(index), f"camp-{index}", "same-source", start, end, str(path),
                    "Title", "Disclosure", [], "", passthrough=True)
        ledger.record_clip(clip)
        ledger.record_campaign(Campaign(f"camp-{index}", "Camp", "", 1, 10,
                                        ["youtube_shorts"], ""))
        ledger.add_library_clip(clip, checklist={}, status="ready")
    class Uploader:
        calls = []
        def upload(self, clip, *, dry_run=False): self.calls.append(clip)
    uploader = Uploader()
    result = distribute_ready({"live": True, "channels": ["@one", "@two"],
                               "approved_campaign_ids": ["camp-0", "camp-1"]},
                              home=tmp_path, uploader=uploader)
    assert result["uploads"] == 0
    assert uploader.calls == []


def test_windows_runner_and_scheduler_are_present_and_live_is_opt_in():
    scripts = VENTURE_DIR / "scripts"
    runner = (scripts / "run_hourly.ps1").read_text(encoding="utf-8")
    installer = (scripts / "install_schedule.ps1").read_text(encoding="utf-8")
    assert "scripts.producer" in runner and "scripts.distributor --live" in runner
    assert "CLIP_HOME" in runner and "logs" in runner
    assert "Register-ScheduledTask" in installer
    for script in (runner, installer):
        assert '[string]$Python = ""' in script
        assert '.venv\\Scripts\\python.exe' in script
        assert 'C:\\Users\\benja\\glacier-dev\\.venv\\Scripts\\python.exe' in script
        assert '$Python = "python"' in script
    assert 'Push-Location $ventureDir' in runner
    assert '-WorkingDirectory $ventureDir' in installer
    assert "$Live" in installer and "$config.live = [bool]$Live.IsPresent" in installer


@pytest.mark.skipif(os.environ.get("WHOP_SOURCE_SMOKE") != "1", reason="set WHOP_SOURCE_SMOKE=1 for public Drive/Dropbox smoke")
def test_public_drive_and_dropbox_network_smoke(tmp_path):
    from scripts.sources import fetch_source
    drive_url = os.environ["WHOP_PUBLIC_DRIVE_FILE"]
    dropbox_url = os.environ["WHOP_PUBLIC_DROPBOX_FILE"]
    for index, url in enumerate((drive_url, dropbox_url)):
        result = fetch_source(url, f"smoke-{index}", cache_dir=tmp_path / str(index),
                              max_bytes=int(os.environ.get("WHOP_SOURCE_SMOKE_MAX_BYTES", "50000000")),
                              timeout_s=90)
        assert result.path.is_file() and result.path.stat().st_size > 0
