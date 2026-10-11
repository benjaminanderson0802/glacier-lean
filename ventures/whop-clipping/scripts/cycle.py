"""Manual convenience helper: run Producer once, then Distributor once."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .interfaces import Campaign, Clip, Post
from .ledger import clip_home


DEFAULT_CHANNELS = [
    "@frameandmomentdesk", "@highlightdesknotes", "@replaynotesdesk", "@quickreplaydesk",
    "@dailycutnotes", "@clipcurrentdesk", "@sceneselectnotes", "@momentarchivedesk",
    "@thecliproomnotes", "@contextclipsdesk",
]


class FakeScout:
    def __init__(self, campaigns=()): self.campaigns = list(campaigns)
    def list_campaigns(self): return list(self.campaigns)


class FakeUploader:
    def __init__(self): self.uploads = []
    def upload(self, clip, *, dry_run=False):
        self.uploads.append((clip, dry_run))
        return Post(clip.id, clip.channel_handle, "youtube_shorts", f"fake-{clip.id}",
                    f"https://youtube.test/shorts/{clip.id}", datetime.now(timezone.utc).isoformat())
    def refresh_statuses(self): return []


class FakeSubmitter:
    def __init__(self): self.submissions = []
    def submit(self, campaign, post, *, dry_run=False):
        self.submissions.append((campaign, post, dry_run))
        return f"manual-{post.clip_id}"


def load_plugin(spec: str, *, config=None):
    import importlib
    if not spec or "." not in spec:
        raise ValueError("plugin must be configured as module.ClassName")
    module_name, class_name = spec.rsplit(".", 1)
    cls = getattr(importlib.import_module(module_name), class_name)
    try:
        return cls(config=config)
    except TypeError:
        return cls()


def _campaign(value):
    return value if isinstance(value, Campaign) else Campaign(**dict(value))


def _campaign_eligible(campaign, config, ledger):
    platforms = {str(value).lower().replace(" ", "_") for value in campaign.platforms}
    rules = campaign.rules_text.lower()
    youtube_allowed = bool(platforms.intersection({"youtube", "youtube_shorts", "shorts"}))
    allowed_line = re.search(r"(?:allowed|eligible) platforms?\s*[:=]\s*([^\n.]+)", campaign.rules_text, re.I)
    if (re.search(r"(?:youtube(?: shorts)?).{0,35}(?:not allowed|prohibited|forbidden|excluded)|(?:no|do not use|don't use)\s+youtube", rules)
            or (allowed_line and not re.search(r"youtube|shorts", allowed_line.group(1), re.I))):
        youtube_allowed = False
    if not youtube_allowed or campaign.cpm_usd <= 0:
        return False
    if campaign.budget_left_usd is not None and campaign.budget_left_usd <= 0:
        return False
    if campaign.id in set(config.get("paused_campaign_ids", [])):
        return False
    if campaign.id not in set(config.get("approved_campaign_ids", [])):
        return False
    return not all(ledger.is_paused(channel, campaign.id) for channel in config.get("channels", DEFAULT_CHANNELS))


def run_cycle(config, *, home=None, scout=None, uploader=None, submitter=None, dry_run=True,
              campaign_clips=None, **kwargs):
    from .producer import produce_ready
    from .distributor import distribute_ready
    home = clip_home(home)
    producer = produce_ready(config, home=home, scout=scout, campaign_clips=campaign_clips,
                             target_stock=int(config.get("target_library_stock", 20)))
    distributor = distribute_ready(config, home=home, uploader=uploader, submitter=submitter,
                                   dry_run=dry_run, **{key: value for key, value in kwargs.items()
                                                       if key in {"now_fn", "rng", "sleep_fn", "alert_fn"}})
    from .ledger import Ledger
    ledger = Ledger(home)
    queue_count = len(ledger.submit_queue())
    ledger.event("cycle_completed", {"manual_run": True, "dry_run": dry_run, "producer": producer,
                                            "distributor": distributor})
    return {"dry_run": dry_run, "campaigns": producer["campaigns"], "clips": producer["produced"],
            "uploads": distributor["uploads"], "submissions": 0,
            "queued_submissions": queue_count,
            "skipped": max(distributor["skipped"], producer["qa_failures"]),
            "producer": producer, "distributor": distributor}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Producer and Distributor once for manual use")
    parser.add_argument("--config", type=Path, default=clip_home() / "config.json")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--home", type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    dry_run = not args.live or not config.get("live", False)
    print(json.dumps(run_cycle(config, home=args.home, dry_run=dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
