"""Local campaign inbox Scout; it never connects to Whop."""
from __future__ import annotations

import json
from pathlib import Path

from .ledger import clip_home


class LocalCampaignScout:
    """Read campaign records the owner placed in CLIP_HOME/campaigns.json."""
    def __init__(self, config=None):
        home = Path(config["clip_home"]) if config and config.get("clip_home") else clip_home()
        self.path = home / "campaigns.json"

    def list_campaigns(self):
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("campaigns", [])
