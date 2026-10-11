"""Official YouTube Data API v3 Shorts uploader; all runtime state stays in CLIP_HOME."""
from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

if __package__:
    from .interfaces import Clip, Post
    from .ledger import Ledger, clip_home
else:
    from scripts.interfaces import Clip, Post
    from scripts.ledger import Ledger, clip_home


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
MAX_UPLOADS_PER_DAY = 90
QUOTA_TIMEZONE = ZoneInfo("America/Los_Angeles")


def _handle_key(handle: str) -> str:
    return handle.lower()


def load_credentials(handle: str, home: Path):
    token_file = home / "tokens" / f"{_handle_key(handle)}.json"
    if not token_file.is_file():
        raise FileNotFoundError(f"No YouTube OAuth token for {handle}: {token_file}")
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid:
        raise RuntimeError(f"YouTube OAuth token for {handle} is invalid; reauthorize it")
    return creds


def _http_error_data(exc: HttpError) -> tuple[int, set[str], str]:
    status = int(getattr(exc.resp, "status", 0) or 0)
    message = str(exc)
    reasons: set[str] = set()
    try:
        data = json.loads(exc.content.decode("utf-8"))
        error = data.get("error", {})
        message = str(error.get("message") or message)
        for item in error.get("errors", []):
            if item.get("reason"):
                reasons.add(str(item["reason"]).lower())
    except (ValueError, AttributeError, TypeError):
        pass
    return status, reasons, message


def _retryable(exc: HttpError) -> bool:
    status, _, _ = _http_error_data(exc)
    return status >= 500


class YouTubeUploader:
    """Resumable uploader implementing the shared Uploader protocol."""

    def __init__(self, config=None, *, ledger=None, service=None, home=None,
                 retry_sleep=time.sleep, now_fn=lambda: datetime.now(timezone.utc), rng=None):
        self.config = dict(config or {})
        self.home = clip_home(home)
        self.ledger = ledger or Ledger(self.home)
        self.service = service
        self._services = {}
        self.retry_sleep = retry_sleep
        self.now_fn = now_fn
        self.rng = rng or random.Random()

    def _service_for(self, handle):
        if self.service is not None:
            return self.service
        if handle not in self._services:
            credentials = load_credentials(handle, self.home)
            self._services[handle] = build("youtube", "v3", credentials=credentials,
                                           cache_discovery=False)
        return self._services[handle]

    def refresh_statuses(self):
        """Refresh all configured channels; the caller records any pauses in the ledger."""
        if not self.config.get("live", False):
            return []
        if self.config.get("refresh_channel_stats", True) is False:
            return []
        if __package__:
            from .channels import refresh_all_channels
        else:
            from scripts.channels import refresh_all_channels
        return refresh_all_channels(
            home=self.home, ledger=self.ledger,
            service_factory=lambda handle: self._service_for(handle),
            now=self.now_fn(),
            minimum_posts=int(self.config.get("view_collapse_min_posts", 6)),
            collapse_ratio=float(self.config.get("view_collapse_ratio", 0.2)),
        )

    def _today_uploads(self):
        today = self.now_fn().astimezone(QUOTA_TIMEZONE).date().isoformat()
        return sum(
            int(event["details"].get("count", 0))
            for event in self.ledger.events()
            if event["kind"] == "youtube_quota_reservation"
            and event["details"].get("day") == today
        )

    def quota_stopped_today(self) -> bool:
        today = self.now_fn().astimezone(QUOTA_TIMEZONE).date().isoformat()
        return any(event["kind"] == "youtube_quota_stop"
                   and event["details"].get("day") == today
                   for event in self.ledger.events())

    def _reserve_upload(self, clip):
        if self.quota_stopped_today():
            raise RuntimeError("YouTube quota was exceeded; uploads are stopped for today")
        configured_cap = min(MAX_UPLOADS_PER_DAY,
                             max(0, int(self.config.get("global_daily_cap", MAX_UPLOADS_PER_DAY))))
        cap = min(MAX_UPLOADS_PER_DAY, configured_cap)
        if self._today_uploads() >= cap:
            raise RuntimeError(f"YouTube daily upload safety cap reached ({cap}); uploads stop for today")
        now = self.now_fn()
        quota_day = now.astimezone(QUOTA_TIMEZONE).date().isoformat()
        self.ledger.event("youtube_quota_reservation", {
            "day": quota_day, "count": 1, "quota_units": 1,
            "bucket": "Video Uploads", "clip_id": clip.id,
            "channel": clip.channel_handle,
        })

    def _validate_clip(self, clip):
        if not Path(clip.path).is_file():
            raise FileNotFoundError(f"Clip media is missing: {clip.path}")
        title = " ".join(str(clip.title or "").split())
        if not title:
            raise ValueError("YouTube title is required")
        title = title[:100]
        hashtags = list(dict.fromkeys(str(tag).strip() for tag in (clip.hashtags or []) if str(tag).strip()))
        description = str(clip.description or "").strip()
        if hashtags:
            missing = [tag for tag in hashtags if tag.casefold() not in description.casefold()]
            if missing:
                description = "\n\n".join(part for part in (description, " ".join(missing)) if part)
        if not description:
            raise ValueError("Campaign description or disclosure is required")
        return title, description, hashtags

    def upload(self, clip: Clip, *, dry_run: bool = False) -> Post:
        title, description, hashtags = self._validate_clip(clip)
        if dry_run:
            return Post(clip.id, clip.channel_handle, "youtube_shorts", f"dry-run-{clip.id}",
                        "", self.now_fn().isoformat())
        if not self.config.get("live", False):
            raise RuntimeError("live upload refused: set live=true in the private config")
        if self.ledger.is_paused(clip.channel_handle, clip.campaign_id):
            raise RuntimeError(f"YouTube channel or campaign is paused: {clip.channel_handle}")
        if self.ledger.submitted_or_posted(clip.id):
            raise RuntimeError(f"Clip {clip.id} has already been posted or submitted")
        if self.ledger.segment_conflicts(clip.source_id, clip.start_s, clip.end_s,
                                         channel_handle=clip.channel_handle,
                                         except_clip_id=clip.id):
            raise RuntimeError("overlapping source segment is already assigned to another channel")
        assigned = self.ledger.existing_channel(clip.source_id, clip.start_s, clip.end_s)
        if assigned and assigned != clip.channel_handle:
            raise RuntimeError(f"source segment is already assigned to {assigned}")
        self.ledger.record_clip(clip)
        # The quota event is written before sending the request so a crash cannot bypass the cap.
        self._reserve_upload(clip)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": hashtags,
                "categoryId": str(self.config.get("category_id", "22")),
            },
            "status": {
                "privacyStatus": "public" if self.config.get("live", False) else "private",
                "selfDeclaredMadeForKids": False,
            },
        }
        contains_synthetic = getattr(clip, "contains_synthetic_media", None)
        if contains_synthetic is None:
            contains_synthetic = self.config.get("contains_synthetic_media")
        if contains_synthetic is not None:
            body["status"]["containsSyntheticMedia"] = bool(contains_synthetic)
        media = MediaFileUpload(clip.path, mimetype="video/*", chunksize=8 * 1024 * 1024,
                                resumable=True)
        request = self._service_for(clip.channel_handle).videos().insert(
            part="snippet,status", body=body, media_body=media,
        )
        response = None
        retries = 0
        max_retries = max(0, min(5, int(self.config.get("upload_retries", 3))))
        while response is None:
            try:
                _, response = request.next_chunk()
                retries = 0
            except HttpError as exc:
                status, reasons, message = _http_error_data(exc)
                if "quotaexceeded" in reasons or "dailylimitexceeded" in reasons:
                    today = self.now_fn().astimezone(QUOTA_TIMEZONE).date().isoformat()
                    self.ledger.event("youtube_quota_stop", {"day": today, "channel": clip.channel_handle,
                                                              "reason": ",".join(sorted(reasons))})
                    raise RuntimeError("YouTube quota exceeded; uploads are stopped for today") from exc
                lower_message = message.lower()
                terms_like = any(token in lower_message for token in
                                 ("terms", "strike", "suspended", "terminated", "policy violation"))
                if status == 403 or terms_like:
                    reason = f"YouTube API forbidden/terms/strike error ({status}): {message}"
                    self.ledger.pause(clip.channel_handle, None, reason)
                    self.ledger.event("youtube_upload_paused", {"channel": clip.channel_handle,
                                                                 "clip_id": clip.id, "reason": reason})
                    raise RuntimeError(reason) from exc
                if not _retryable(exc) or retries >= max_retries:
                    self.ledger.event("youtube_upload_failed", {"clip_id": clip.id,
                                                                 "channel": clip.channel_handle,
                                                                 "status": status, "message": message})
                    raise
                delay = min(60.0, 2 ** retries + self.rng.random())
                self.retry_sleep(delay)
                retries += 1
        video_id = str(response.get("id", ""))
        if not video_id:
            raise RuntimeError("YouTube upload response did not include a video id")
        post = Post(clip.id, clip.channel_handle, "youtube_shorts", video_id,
                    f"https://youtube.com/shorts/{video_id}", self.now_fn().isoformat())
        self.ledger.record_post(post)
        self.ledger.event("youtube_upload_completed", {"clip_id": clip.id, "channel": clip.channel_handle,
                                                        "video_id": video_id, "quota_units": 1})
        return post
