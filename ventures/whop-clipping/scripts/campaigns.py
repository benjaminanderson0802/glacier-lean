"""Repository campaign briefs with private CLIP_HOME overrides."""
from __future__ import annotations

import json
from pathlib import Path

from .interfaces import Campaign


def _read_campaign(folder: Path, override: Path | None = None) -> Campaign:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if override and (override / "summary.json").is_file():
        summary.update(json.loads((override / "summary.json").read_text(encoding="utf-8")))
    rules_path = override / "rules.txt" if override and (override / "rules.txt").is_file() else folder / "rules.txt"
    sources_path = override / "sources.txt" if override and (override / "sources.txt").is_file() else folder / "sources.txt"
    rules = rules_path.read_text(encoding="utf-8") if rules_path.is_file() else str(summary.get("rules_text", ""))
    sources = []
    if sources_path.is_file():
        sources = [{"url": line.strip()} for line in sources_path.read_text(encoding="utf-8").splitlines()
                   if line.strip().startswith(("https://", "http://"))]
    fields = Campaign.__dataclass_fields__
    values = {key: summary[key] for key in fields if key in summary}
    values.setdefault("id", summary.get("uuid", folder.name))
    values.setdefault("name", values["id"])
    values.setdefault("url", "")
    values.setdefault("cpm_usd", 0)
    values.setdefault("budget_left_usd", None)
    values.setdefault("platforms", ["youtube_shorts"])
    values["rules_text"] = rules
    values["source_links"] = sources
    campaign = Campaign(**values)
    # Extra brief fields are carried in the instance payload for status/eligibility.
    campaign.eligible_for_new_youtube_shorts_channels = summary.get(
        "eligible_for_new_youtube_shorts_channels", "No")
    campaign.owner_requirements = summary.get("owner_requirements", summary.get("needs_owner_action", []))
    if isinstance(campaign.owner_requirements, str):
        campaign.owner_requirements = [campaign.owner_requirements]
    campaign.requires_draft_preapproval = bool(summary.get("requires_draft_preapproval", False))
    return campaign


def load_campaign_registry(repo_dir: Path, home: Path, *, campaigns_dir: Path | None = None) -> list[Campaign]:
    """Load configured briefs, overlaying each matching private CLIP_HOME brief."""
    repo_dir, home = Path(repo_dir), Path(home)
    repo_campaigns = Path(campaigns_dir) if campaigns_dir is not None else repo_dir / "campaigns"
    home_campaigns = home / "campaigns"
    repo_folders = {path.name: path for path in repo_campaigns.iterdir()
                    if path.is_dir() and (path / "summary.json").is_file()} if repo_campaigns.is_dir() else {}
    home_folders = {path.name: path for path in home_campaigns.iterdir()
                    if path.is_dir() and (path / "summary.json").is_file()} if home_campaigns.is_dir() else {}
    return [_read_campaign(repo_folders[key] if key in repo_folders else home_folders[key], home_folders.get(key))
            for key in sorted(repo_folders.keys() | home_folders.keys())]


def allocate_daily_campaign_targets(campaigns, total=80, *, capacities=None, feedback=None):
    """Capacity-bounded allocation weighted by CPM, budget and owner feedback."""
    rows = [row if isinstance(row, dict) else {
        "id": row.id, "cpm_usd": row.cpm_usd, "budget_left_usd": row.budget_left_usd
    } for row in campaigns]
    if not rows:
        return {}
    total = max(0, int(total))
    capacities = capacities or {}
    feedback = feedback or {}
    weights = [max(0.0, float(row.get("cpm_usd") or 0) * float(row.get("budget_left_usd") or 0)) *
               float(feedback.get(row["id"], {}).get("factor", 1)) for row in rows]
    if not any(weights):
        weights = [float(feedback.get(row["id"], {}).get("factor", 1)) for row in rows]
    result = {row["id"]: 0 for row in rows}
    # Allocate at most the number of distinct usable moments. Reassign exhausted
    # shares, preserving the CPM x budget ranking and an initial campaign floor.
    for _ in range(total):
        available = [i for i, row in enumerate(rows) if result[row["id"]] < max(0, int(capacities.get(row["id"], total)))]
        if not available:
            break
        index = max(available, key=lambda i: (result[rows[i]["id"]] == 0,
                                              weights[i] / (result[rows[i]["id"]] + 1), rows[i]["id"]))
        result[rows[index]["id"]] += 1
    return result
