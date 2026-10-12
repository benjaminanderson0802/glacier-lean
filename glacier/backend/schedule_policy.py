"""Small, deterministic policies used around DBOS's durable scheduler."""
from datetime import timedelta

from dbos._croniter import croniter


def missed_run(policy, occurrences):
    """Return the newest missed occurrence once, or None when missed work is skipped."""
    if policy == "skip" or not occurrences:
        return None
    if policy != "run_once":
        raise ValueError("missed_run must be 'run_once' or 'skip'")
    return max(occurrences)


def overlap_action(policy, active):
    if policy not in ("queue", "skip"):
        raise ValueError("overlap must be 'queue' or 'skip'")
    if not active:
        return "run"
    return policy


def stuck_reason(status, age_seconds, timeout_seconds):
    if status != "running" or age_seconds <= timeout_seconds:
        return None
    minutes = max(1, round(timeout_seconds / 60))
    return f"This run timed out after {minutes} minute{'s' if minutes != 1 else ''}."


def stale_cutoff(timeout_seconds):
    return timedelta(seconds=max(1, timeout_seconds))


def next_run(cron, now):
    return croniter(cron, now, second_at_beginning=True).get_next(type(now)).isoformat()
