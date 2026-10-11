"""YouTube channel authorization, view-collapse checks, and safe posting slots."""
from __future__ import annotations

import random
import statistics
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

if __package__:
    from .ledger import Ledger, clip_home
    from .youtube_upload import load_credentials
else:
    from scripts.ledger import Ledger, clip_home
    from scripts.youtube_upload import load_credentials


CHANNEL_HANDLES = [
    "@frameandmomentdesk", "@highlightdesknotes", "@replaynotesdesk", "@quickreplaydesk",
    "@dailycutnotes", "@clipcurrentdesk", "@sceneselectnotes", "@momentarchivedesk",
    "@thecliproomnotes", "@contextclipsdesk",
]
GLOBAL_DAILY_CAP = 90


def youtube_readonly(handle, *, home=None, service=None):
    if service is not None:
        return service
    root = clip_home(home)
    credentials = load_credentials(handle, root)
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def detect_view_collapse(posts, *, now=None, minimum_posts=6, collapse_ratio=0.2):
    now = now or datetime.now(timezone.utc)
    recent_start = now - timedelta(days=7)
    baseline_start = now - timedelta(days=28)
    recent = [int(views) for published, views in posts if recent_start <= published <= now]
    baseline = [int(views) for published, views in posts if baseline_start <= published < recent_start]
    if len(recent) + len(baseline) < max(6, int(minimum_posts)) or not recent or not baseline:
        return {"collapsed": False, "recent_median": None, "baseline_median": None,
                "recent_posts": len(recent), "baseline_posts": len(baseline)}
    recent_median = statistics.median(recent)
    baseline_median = statistics.median(baseline)
    collapsed = baseline_median > 0 and recent_median < baseline_median * max(0.0, min(1.0, collapse_ratio))
    return {"collapsed": collapsed, "recent_median": recent_median,
            "baseline_median": baseline_median, "recent_posts": len(recent),
            "baseline_posts": len(baseline)}


def snapshot_channel(handle, service=None, ledger=None, *, home=None, now=None,
                     minimum_posts=6, collapse_ratio=0.2):
    ledger = ledger or Ledger(clip_home(home))
    youtube = youtube_readonly(handle, home=home, service=service)
    channel_result = youtube.channels().list(part="id,snippet,contentDetails", forHandle=handle.lstrip("@"),
                                             maxResults=1).execute()
    items = channel_result.get("items", [])
    if not items:
        # Resolve linked OAuth channel in cases where the handle filter is unavailable.
        items = youtube.channels().list(part="id,snippet,contentDetails", mine=True,
                                        maxResults=1).execute().get("items", [])
    if not items:
        raise RuntimeError(f"No YouTube channel found for {handle}")
    channel = items[0]
    uploads = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads:
        raise RuntimeError(f"YouTube uploads playlist missing for {handle}")
    items_by_id = {}
    page_token = None
    for _ in range(20):
        page = youtube.playlistItems().list(part="snippet,contentDetails", playlistId=uploads,
                                            maxResults=50, pageToken=page_token).execute()
        for item in page.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                items_by_id[video_id] = item
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    videos = []
    video_ids = list(items_by_id)
    for start in range(0, len(video_ids), 50):
        batch = youtube.videos().list(part="snippet,statistics", id=",".join(video_ids[start:start + 50]),
                                      maxResults=50).execute()
        videos.extend(batch.get("items", []))
    now = now or datetime.now(timezone.utc)
    posts = []
    for video in videos:
        published = video.get("snippet", {}).get("publishedAt")
        if not published:
            continue
        published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if published_at < now - timedelta(days=28):
            continue
        views = int(video.get("statistics", {}).get("viewCount", 0))
        posts.append((published_at, views, str(video.get("id", ""))))
    result = detect_view_collapse([(published, views) for published, views, _ in posts],
                                 now=now, minimum_posts=minimum_posts,
                                 collapse_ratio=collapse_ratio)
    snapshot = {"channel_handle": handle, "channel_id": channel.get("id"),
                "channel_title": channel.get("snippet", {}).get("title"),
                "post_count_28d": len(posts), **result}
    ledger.event("youtube_channel_snapshot", snapshot)
    if result["collapsed"]:
        ledger.pause(handle, None,
                     f"YouTube views collapsed: 7-day median {result['recent_median']} "
                     f"vs prior 21-day median {result['baseline_median']}")
        snapshot["views_collapsed"] = True
    else:
        snapshot["views_collapsed"] = False
    return snapshot


def schedule_slots(start, *, count, daily_channel_cap=3, global_remaining=GLOBAL_DAILY_CAP,
                   min_spacing_hours=2, jitter_minutes=45, seed=None):
    """Return deterministic-for-seed randomized UTC slots within safe daily limits."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    cap = min(max(0, int(daily_channel_cap)), max(0, int(count)),
              max(0, int(global_remaining)), GLOBAL_DAILY_CAP)
    if not cap:
        return []
    spacing = timedelta(hours=max(2.0, float(min_spacing_hours)))
    jitter = max(0, int(jitter_minutes))
    rng = random.Random(seed)
    slots = [start + timedelta(minutes=rng.randint(0, jitter))]
    for _ in range(1, cap):
        slots.append(slots[-1] + spacing + timedelta(minutes=rng.randint(0, jitter)))
    return slots


def refresh_all_channels(*, home=None, ledger=None, service_factory=None, now=None,
                         minimum_posts=6, collapse_ratio=0.2):
    root = clip_home(home)
    ledger = ledger or Ledger(root)
    results = []
    for handle in CHANNEL_HANDLES:
        service = service_factory(handle) if service_factory else None
        try:
            results.append(snapshot_channel(handle, service, ledger, home=root, now=now,
                                            minimum_posts=minimum_posts,
                                            collapse_ratio=collapse_ratio))
        except Exception as exc:
            ledger.event("youtube_channel_snapshot_error", {"channel": handle, "error": str(exc)})
            results.append({"channel_handle": handle, "error": str(exc)})
    return results
