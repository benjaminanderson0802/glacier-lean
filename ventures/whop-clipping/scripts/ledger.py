"""Idempotent local SQLite ledger for clip provenance and external actions."""
from __future__ import annotations

import json
import os
import sqlite3
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .interfaces import Post


def clip_home(home: Optional[Path] = None) -> Path:
    return Path(home or os.environ.get("CLIP_HOME", Path.home() / ".glacier/ventures/whop-clipping"))


class Ledger:
    def __init__(self, home: Optional[Path] = None):
        self.home = clip_home(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "ledger.db"
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
                    cpm_usd REAL NOT NULL, budget_left_usd REAL, rules_text TEXT NOT NULL,
                    payload TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, url TEXT NOT NULL, path TEXT NOT NULL,
                    sha256 TEXT NOT NULL, provenance TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clips (
                    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, source_id TEXT NOT NULL,
                    start_s REAL NOT NULL, end_s REAL NOT NULL, path TEXT NOT NULL,
                    channel_handle TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS clips_source_segment ON clips(source_id, start_s, end_s);
                CREATE TABLE IF NOT EXISTS posts (
                    clip_id TEXT NOT NULL, channel_handle TEXT NOT NULL, platform TEXT NOT NULL,
                    video_id TEXT NOT NULL, url TEXT NOT NULL, posted_at TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(platform, video_id), UNIQUE(clip_id, channel_handle)
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    campaign_id TEXT NOT NULL, clip_id TEXT NOT NULL, submission_id TEXT NOT NULL,
                    status TEXT NOT NULL, reason TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, clip_id), UNIQUE(submission_id)
                );
                CREATE TABLE IF NOT EXISTS pauses (
                    channel TEXT NOT NULL, campaign_id TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL,
                    paused_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(channel, campaign_id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                    created_at TEXT NOT NULL, details TEXT NOT NULL, idempotency_key TEXT UNIQUE
                );
            """)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def event(self, kind: str, details: dict, idempotency_key: Optional[str] = None):
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO events(kind,created_at,details,idempotency_key) VALUES(?,?,?,?)",
                       (kind, self._now(), json.dumps(details, sort_keys=True), idempotency_key))

    def events(self):
        with self._connect() as db:
            return [dict(row, details=json.loads(row["details"])) for row in db.execute("SELECT * FROM events ORDER BY id")]

    def record_campaign(self, campaign):
        payload = campaign.__dict__
        with self._connect() as db:
            db.execute("""INSERT INTO campaigns VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,url=excluded.url,
                cpm_usd=excluded.cpm_usd,budget_left_usd=excluded.budget_left_usd,
                rules_text=excluded.rules_text,payload=excluded.payload,updated_at=excluded.updated_at""",
                (campaign.id, campaign.name, campaign.url, campaign.cpm_usd, campaign.budget_left_usd,
                 campaign.rules_text, json.dumps(payload, sort_keys=True), self._now()))

    def record_source(self, source_id: str, url: str, path: Path, sha256: str, provenance: dict):
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?)",
                       (source_id, url, str(path), sha256, json.dumps(provenance, sort_keys=True), self._now()))

    def record_clip(self, clip):
        with self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO clips VALUES(?,?,?,?,?,?,?,?,?)""",
                       (clip.id, clip.campaign_id, clip.source_id, clip.start_s, clip.end_s, clip.path,
                        clip.channel_handle, json.dumps(clip.__dict__, sort_keys=True), self._now()))
        self.event("clip_created", {"clip_id": clip.id, "source_id": clip.source_id,
                                     "start_s": clip.start_s, "end_s": clip.end_s,
                                     "channel": clip.channel_handle}, f"clip:{clip.id}")

    def record_post(self, post: Post) -> bool:
        payload = json.dumps(post.__dict__, sort_keys=True)
        with self._connect() as db:
            cur = db.execute("INSERT OR IGNORE INTO posts VALUES(?,?,?,?,?,?,?)",
                              (post.clip_id, post.channel_handle, post.platform, post.video_id,
                               post.url, post.posted_at, payload))
        if cur.rowcount:
            self.event("post_recorded", post.__dict__, f"post:{post.platform}:{post.video_id}")
        return bool(cur.rowcount)

    def record_submission(self, campaign_id, clip_id, submission_id, status, reason):
        with self._connect() as db:
            previous = db.execute("SELECT status,reason FROM submissions WHERE campaign_id=? AND clip_id=?",
                                  (campaign_id, clip_id)).fetchone()
            db.execute("""INSERT INTO submissions VALUES(?,?,?,?,?,?)
                ON CONFLICT(campaign_id,clip_id) DO UPDATE SET submission_id=excluded.submission_id,
                status=excluded.status,reason=excluded.reason,updated_at=excluded.updated_at""",
                (campaign_id, clip_id, submission_id, status, reason, self._now()))
        changed = previous is None or (previous["status"], previous["reason"]) != (status, reason)
        if changed:
            self.event("submission_recorded", {"campaign_id": campaign_id, "clip_id": clip_id,
                "submission_id": submission_id, "status": status, "reason": reason},
                f"submission:{campaign_id}:{clip_id}:{status}:{reason}")
        if str(status).lower() == "flagged" or "flagged" in str(reason).lower():
            with self._connect() as db:
                clip_row = db.execute("SELECT channel_handle FROM clips WHERE id=?", (clip_id,)).fetchone()
            if clip_row and clip_row["channel_handle"]:
                self.pause(clip_row["channel_handle"], campaign_id, f"Whop marked submission flagged: {reason}")
        return changed

    def pause(self, channel: str, campaign_id: Optional[str], reason: str):
        key = campaign_id or ""
        with self._connect() as db:
            db.execute("""INSERT INTO pauses VALUES(?,?,?,?,1)
                ON CONFLICT(channel,campaign_id) DO UPDATE SET reason=excluded.reason,
                paused_at=excluded.paused_at,active=1""", (channel, key, reason, self._now()))
        self.event("paused", {"channel": channel, "campaign_id": campaign_id, "reason": reason},
                   f"pause:{channel}:{key}:{reason}")

    def is_paused(self, channel: str, campaign_id: Optional[str]) -> bool:
        with self._connect() as db:
            return db.execute("""SELECT 1 FROM pauses WHERE channel=? AND active=1
                AND (campaign_id='' OR campaign_id=?) LIMIT 1""", (channel, campaign_id or "")).fetchone() is not None

    def overlap_used(self, source_id: str, start_s: float, end_s: float) -> bool:
        return bool(self.segment_conflicts(source_id, start_s, end_s))

    def segment_conflicts(self, source_id: str, start_s: float, end_s: float,
                          *, channel_handle: Optional[str] = None, except_clip_id: Optional[str] = None):
        if end_s <= start_s:
            raise ValueError("end_s must be greater than start_s")
        with self._connect() as db:
            rows = db.execute("SELECT id,start_s,end_s,channel_handle FROM clips WHERE source_id=?", (source_id,)).fetchall()
        conflicts = []
        for row in rows:
            overlap = max(0.0, min(end_s, row["end_s"]) - max(start_s, row["start_s"]))
            if overlap / min(end_s - start_s, row["end_s"] - row["start_s"]) <= 0.30:
                continue
            if (except_clip_id and row["id"] == except_clip_id
                    and (channel_handle is None or row["channel_handle"] == channel_handle)):
                continue
            if channel_handle is None or row["channel_handle"] != channel_handle:
                conflicts.append(dict(row))
        return conflicts

    def existing_channel(self, source_id: str, start_s: float, end_s: float):
        with self._connect() as db:
            row = db.execute("""SELECT channel_handle FROM clips WHERE source_id=?
                AND abs(start_s-?)<0.01 AND abs(end_s-?)<0.01 AND channel_handle IS NOT NULL
                ORDER BY created_at LIMIT 1""", (source_id, start_s, end_s)).fetchone()
        return row[0] if row else None

    def posts_today(self, channel: str, today: Optional[str] = None) -> int:
        day = today or date.today().isoformat()
        with self._connect() as db:
            return db.execute("SELECT count(*) FROM posts WHERE channel_handle=? AND substr(posted_at,1,10)=?",
                              (channel, day)).fetchone()[0]

    def global_posts_today(self, today: Optional[str] = None) -> int:
        day = today or date.today().isoformat()
        with self._connect() as db:
            return db.execute("SELECT count(*) FROM posts WHERE substr(posted_at,1,10)=?", (day,)).fetchone()[0]

    def last_post_at(self, channel: str):
        with self._connect() as db:
            row = db.execute("SELECT posted_at FROM posts WHERE channel_handle=? ORDER BY posted_at DESC LIMIT 1",
                              (channel,)).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def submitted_or_posted(self, clip_id: str) -> bool:
        with self._connect() as db:
            return bool(db.execute("SELECT 1 FROM posts WHERE clip_id=? UNION SELECT 1 FROM submissions WHERE clip_id=?",
                                   (clip_id, clip_id)).fetchone())

    def record_views(self, channel: str, video_id: str, views: int, *, collapse_ratio: float = 0.2):
        views = max(0, int(views))
        history = [event for event in self.events() if event["kind"] == "youtube_views"
                   and event["details"].get("channel") == channel]
        baseline_values = [int(event["details"]["views"]) for event in history[-7:]]
        baseline = statistics.median(baseline_values) if len(baseline_values) >= 3 else None
        observed_at = self._now()
        minute = observed_at[:16]
        self.event("youtube_views", {"channel": channel, "video_id": video_id, "views": views,
                                      "observed_at": observed_at, "baseline": baseline},
                   f"youtube_views:{channel}:{video_id}:{minute}")
        collapsed = baseline is not None and baseline > 0 and views < baseline * max(0.0, min(1.0, collapse_ratio))
        if collapsed:
            self.pause(channel, None, f"YouTube views collapsed: {views} vs recent median {baseline}")
        return collapsed
