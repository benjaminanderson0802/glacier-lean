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


def allocate_daily_campaign_targets(campaigns, total=40):
    """Largest-remainder allocation weighted by CPM times remaining budget."""
    rows = [row if isinstance(row, dict) else {
        "id": row.id, "cpm_usd": row.cpm_usd, "budget_left_usd": row.budget_left_usd
    } for row in campaigns]
    if not rows:
        return {}
    total = max(int(total), len(rows))
    weights = [max(0.0, float(row.get("cpm_usd") or 0) * float(row.get("budget_left_usd") or 0)) for row in rows]
    if not any(weights):
        weights = [1.0] * len(rows)
    weight_sum = sum(weights)
    exact = [total * weight / weight_sum for weight in weights]
    result = {row["id"]: max(1, int(value)) for row, value in zip(rows, exact)}
    leftovers = total - sum(result.values())
    order = sorted(range(len(rows)), key=lambda idx: (exact[idx] - int(exact[idx]), weights[idx]), reverse=True)
    while leftovers < 0:
        for idx in reversed(order):
            key = rows[idx]["id"]
            if result[key] > 1:
                result[key] -= 1
                leftovers += 1
                if leftovers == 0:
                    break
    for index in range(leftovers):
        result[rows[order[index % len(order)]] ["id"]] += 1
    return result
