"""Owner's output targets, with project-wide quota safety as a hard ceiling."""
import math


def limits(config):
    daily = max(0, int(config.get("daily_target", config.get("daily_target_clips", 80))))
    per_channel = max(0, int(config.get("per_channel_daily", config.get("daily_channel_cap", 8))))
    gap = max(1, int(config.get("min_gap_minutes", float(config.get("min_spacing_hours", 2.5)) * 60)))
    # The legacy keys remain accepted, but cannot relax the 15% safety margin.
    quota = max(0, int(config.get("youtube_daily_insert_quota", 100)))
    cap = min(85, math.floor(quota * .85), max(0, int(config.get("global_daily_cap", 85))))
    return {"daily_target": daily, "per_channel_daily": per_channel,
            "min_gap_minutes": gap, "interval_minutes": max(gap, math.ceil(1440 / max(1, per_channel))),
            "upload_cap": cap}
