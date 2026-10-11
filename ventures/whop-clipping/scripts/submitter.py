"""Manual Whop queue adapter. Whop itself is never accessed programmatically."""
from __future__ import annotations

import os
from pathlib import Path

from .ledger import Ledger, clip_home


class ManualQueueSubmitter:
    def __init__(self, config=None, *, home=None):
        self.home = clip_home(home or (Path(config["clip_home"]) if config and config.get("clip_home") else None))
        self.ledger = Ledger(self.home)

    def submit(self, campaign, post, *, dry_run=False):
        if dry_run:
            return "manual-queue-dry-run"
        clip_row = self.ledger.clip(post.clip_id)
        if not clip_row:
            raise ValueError(f"clip {post.clip_id} is missing from the local ledger")
        from .interfaces import Clip
        clip = Clip(**{key: value for key, value in clip_row.items() if key in Clip.__dataclass_fields__})
        clip.channel_handle = post.channel_handle
        self.ledger.queue_submission(clip, campaign.name, post.url)
        return f"manual-{post.clip_id}"


Submitter = ManualQueueSubmitter
