from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from googleapiclient.discovery import build_from_document
from googleapiclient.http import HttpMockSequence

VENTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VENTURE_DIR))

from scripts.interfaces import Clip, Post
from scripts.ledger import Ledger
from scripts.youtube_upload import YouTubeUploader


def clip(path, *, title="Short title", description="Campaign disclosure #ad", tags=None):
    return Clip("clip-1", "campaign-1", "source-1", 0, 30, str(path), title,
                description, ["#ad", "#shorts"] if tags is None else tags, "@frameandmomentdesk")


def youtube_service(http):
    discovery_path = (Path(__import__("googleapiclient").__file__).parent /
                      "discovery_cache" / "documents" / "youtube.v3.json")
    return build_from_document(discovery_path.read_text(encoding="utf-8"), http=http)


def response(status, body, headers=None):
    return ({"status": str(status), **(headers or {})}, json.dumps(body).encode("utf-8"))


def test_resumable_upload_sets_short_metadata_and_records_post(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture-video")
    http = HttpMockSequence([
        response(200, {}, {"location": "https://upload.example/session/1"}),
        response(200, {"id": "video-123"}),
    ])
    ledger = Ledger(tmp_path / "runtime")
    uploader = YouTubeUploader(config={"live": True, "category_id": "22"}, ledger=ledger,
                               service=youtube_service(http), retry_sleep=lambda _: None)

    post = uploader.upload(clip(media), dry_run=False)

    assert post.video_id == "video-123"
    assert post.url == "https://youtube.com/shorts/video-123"
    assert post.platform == "youtube_shorts"
    assert ledger.global_posts_today() == 1
    assert len(http.request_sequence) == 2
    _, method, body, _ = http.request_sequence[0]
    assert method == "POST"
    metadata = json.loads(body)
    assert metadata["snippet"]["title"] == "Short title"
    assert metadata["snippet"]["tags"] == ["#ad", "#shorts"]
    assert metadata["status"]["privacyStatus"] == "public"
    assert metadata["status"]["selfDeclaredMadeForKids"] is False


def test_upload_dry_run_never_contacts_api_or_records_a_post(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture-video")
    http = HttpMockSequence([])
    ledger = Ledger(tmp_path / "runtime")
    uploader = YouTubeUploader(config={"live": False}, ledger=ledger,
                               service=youtube_service(http))

    post = uploader.upload(clip(media), dry_run=True)

    assert post.video_id == "dry-run-clip-1"
    assert ledger.global_posts_today() == 0
    assert http.request_sequence == []


def test_live_upload_refuses_missing_campaign_disclosure_and_long_title(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture-video")
    http = HttpMockSequence([
        response(200, {}, {"location": "https://upload.example/session/1"}),
        response(200, {"id": "video-long-title"}),
    ])
    uploader = YouTubeUploader(config={"live": True}, ledger=Ledger(tmp_path / "runtime"),
                               service=youtube_service(http), retry_sleep=lambda _: None)

    uploader.upload(clip(media, title="x" * 101), dry_run=False)
    assert len(json.loads(http.request_sequence[0][2])["snippet"]["title"]) == 100
    with pytest.raises(ValueError, match="description"):
        uploader.upload(clip(media, description="", tags=[]), dry_run=False)


def test_quota_exceeded_stops_today_and_forbidden_terms_error_pauses_channel(tmp_path):
    from googleapiclient.errors import HttpError
    from httplib2 import Response

    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture-video")
    ledger = Ledger(tmp_path / "runtime")

    class FailedRequest:
        def next_chunk(self):
            raise HttpError(Response({"status": 403}), b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}')

    class Insert:
        def next_chunk(self):
            return FailedRequest().next_chunk()

    class FailedVideos:
        def insert(self, **kwargs):
            return Insert()

    class FailedService:
        def videos(self):
            return FailedVideos()

    uploader = YouTubeUploader(config={"live": True}, ledger=ledger, service=FailedService())
    with pytest.raises(RuntimeError, match="quota"):
        uploader.upload(clip(media), dry_run=False)
    assert uploader.quota_stopped_today()
    assert ledger.is_paused("@frameandmomentdesk", None) is False

    class TermsRequest:
        def next_chunk(self):
            raise HttpError(Response({"status": 403}),
                            b'{"error":{"errors":[{"reason":"termsOfServiceAcceptanceRequired"}]}}')

    class TermsInsert:
        def next_chunk(self):
            return TermsRequest().next_chunk()

    class TermsVideos:
        def insert(self, **kwargs):
            return TermsInsert()

    terms_ledger = Ledger(tmp_path / "terms-runtime")
    uploader = YouTubeUploader(config={"live": True}, ledger=terms_ledger,
                               service=type("TermsService", (), {"videos": lambda self: TermsVideos()})())
    with pytest.raises(RuntimeError):
        uploader.upload(clip(media, title="another"), dry_run=False)
    assert terms_ledger.is_paused("@frameandmomentdesk", None)


def test_api_calls_retry_server_error_and_clip_length_is_not_changed(tmp_path):
    from googleapiclient.errors import HttpError
    from httplib2 import Response

    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fixture-video")
    ledger = Ledger(tmp_path / "runtime")
    request = type("Request", (), {})()
    request.calls = 0

    class Insert:
        def next_chunk(self):
            return next_chunk()

    def next_chunk():
        request.calls += 1
        if request.calls == 1:
            raise HttpError(Response({"status": 503}), b"temporary backend error")
        return None, {"id": "video-after-retry"}

    request.next_chunk = next_chunk
    class Videos:
        def insert(self, **kwargs):
            self.body = kwargs["body"]
            return Insert()
    videos = Videos()
    uploader = YouTubeUploader(config={"live": True, "category_id": "22"}, ledger=ledger,
                               service=type("Service", (), {"videos": lambda self: videos})(),
                               retry_sleep=lambda _: None)

    post = uploader.upload(clip(media), dry_run=False)

    assert post.video_id == "video-after-retry"
    assert request.calls == 2
    assert videos.body["snippet"]["title"] == "Short title"
    assert videos.body["status"]["privacyStatus"] == "public"


def test_uploader_uses_a_distinct_oauth_service_for_each_channel(monkeypatch, tmp_path):
    import scripts.youtube_upload as upload_module

    built = []
    monkeypatch.setattr(upload_module, "load_credentials", lambda handle, home: handle)
    monkeypatch.setattr(upload_module, "build", lambda *_args, credentials, **_kwargs:
                        built.append(credentials) or object())
    uploader = YouTubeUploader(config={}, ledger=Ledger(tmp_path / "runtime"))

    first = uploader._service_for("@frameandmomentdesk")
    second = uploader._service_for("@highlightdesknotes")

    assert first is not second
    assert built == ["@frameandmomentdesk", "@highlightdesknotes"]


def test_quota_ledger_uses_the_pacific_quota_day(tmp_path):
    now = datetime(2026, 10, 11, 2, tzinfo=timezone.utc)
    ledger = Ledger(tmp_path / "runtime")
    uploader = YouTubeUploader(config={"live": True}, ledger=ledger, now_fn=lambda: now)

    uploader._reserve_upload(clip(tmp_path / "unused.mp4"))

    event = [event for event in ledger.events() if event["kind"] == "youtube_quota_reservation"][-1]
    assert event["details"]["day"] == "2026-10-10"


def test_ledger_counts_upload_across_chicago_to_utc_midnight(tmp_path, monkeypatch):
    import scripts.ledger as ledger_module

    chicago_late = datetime(2026, 10, 11, 23, 30, tzinfo=ZoneInfo("America/Chicago"))
    ledger = Ledger(tmp_path / "runtime")
    post = Post("clip", "@channel", "youtube_shorts", "video", "https://youtube.test/video",
                chicago_late.astimezone(timezone.utc).isoformat())
    ledger.record_post(post)

    frozen = chicago_late

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    monkeypatch.setattr(ledger_module, "datetime", FrozenDateTime)
    assert ledger.global_posts_today() == 1

    frozen = datetime(2026, 10, 12, 0, 30, tzinfo=timezone.utc)
    assert ledger.global_posts_today() == 1
