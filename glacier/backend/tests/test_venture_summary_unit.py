"""Unit coverage for venture summary projection; acceptance belongs to testers."""
from datetime import datetime, timezone

import pytest

from routes import ventures


@pytest.fixture
def summary(monkeypatch):
    graphs, runs = {}, {}
    monkeypatch.setattr(ventures, "_progress", lambda slug: {})
    def load(env_id):
        if env_id not in graphs:
            raise FileNotFoundError(env_id)
        return graphs[env_id]
    monkeypatch.setattr(ventures.runner, "load_env", load)
    monkeypatch.setattr(ventures.store, "list_runs", lambda env_id: runs.get(env_id, []))
    monkeypatch.setattr(ventures.runner, "SCHEDULES_PAUSED", False)
    return graphs, runs


def row(manifest):
    return ventures._venture_row({"slug": "sample", **manifest}, datetime(2026, 10, 10, tzinfo=timezone.utc))


def test_missing_flows_never_get_a_manifest_only_schedule(summary):
    result = row({"flows": ["missing"], "schedule": "0 8 * * *"})
    assert result["next_run"] is None
    assert result["readiness"] == "blocked"
    assert result["run_available"] is False
    assert result["blockers"] == ["missing_flows"]


def test_summary_uses_installed_description_history_and_enabled_schedules(summary):
    graphs, runs = summary
    graphs["sample"] = {"id": "sample", "name": "check public records", "nodes": [
        {"type": "schedule", "config": {"cron": "0 8 * * *"}}]}
    runs["sample"] = [{"run_id": "r1", "env_id": "sample", "status": "done", "started_at": "2026-10-09T23:00:00Z"}]
    result = row({"flows": ["sample"]})
    assert result["description"] == "check public records"
    assert result["last_run"]["run_id"] == "r1"
    assert result["readiness"] == "live"
    assert result["next_run"] == "2026-10-10T08:00:00+00:00"
    graphs["sample"]["enabled"] = False
    result = row({"flows": ["sample"]})
    assert result["next_run"] is None
    assert result["readiness"] == "blocked"


def test_failure_on_another_flow_is_not_hidden_by_a_newer_success(summary):
    graphs, runs = summary
    for name in ("daily", "preview"):
        graphs[name] = {"id": name, "name": name, "nodes": []}
    runs["daily"] = [{"run_id": "bad", "env_id": "daily", "status": "failed", "started_at": "2026-10-09T23:00:00Z"}]
    runs["preview"] = [{"run_id": "good", "env_id": "preview", "status": "done", "started_at": "2026-10-10T00:00:00Z"}]
    result = row({"flows": [{"env_id": "daily", "dry_run_env_id": "preview"}]})
    assert result["last_run"]["run_id"] == "good"
    assert result["readiness"] == "blocked"
    assert "failed_run" in result["blockers"]
    assert result["run_available"] is True


def test_ready_does_not_claim_live_from_preview_and_owner_steps_block(summary):
    graphs, runs = summary
    graphs["preview"] = {"id": "preview", "name": "preview", "nodes": []}
    runs["preview"] = [{"run_id": "ok", "env_id": "preview", "status": "done", "started_at": "2026-10-10T00:00:00Z"}]
    manifest = {"flows": ["preview"], "dry_run_env_id": "preview", "product": {"purpose": "Prepare records."}}
    assert row(manifest)["readiness"] == "ready"
    assert row(manifest)["description"] == "Prepare records."
    manifest["your_steps"] = [{"id": "review", "title": "review records"}]
    assert row(manifest)["blockers"] == ["owner_steps"]


def test_history_survives_missing_flow_and_compares_timezones(summary):
    graphs, runs = summary
    graphs["installed"] = {"id": "installed", "nodes": []}
    runs["removed"] = [{"run_id": "newest", "env_id": "removed", "status": "failed", "started_at": "2026-10-09T23:30:00-05:00"}]
    runs["installed"] = [{"run_id": "older", "env_id": "installed", "status": "done", "started_at": "2026-10-10T01:00:00Z"}]
    result = row({"flows": ["installed", "removed"]})
    assert result["last_run"]["run_id"] == "newest"
    assert result["today"] == {"runs": 2, "completed": 1, "failed": 1}


def test_global_pause_hides_next_run_and_cron_uses_engine_parser(summary, monkeypatch):
    graphs, _ = summary
    graphs["weekly"] = {"id": "weekly", "nodes": [{"type": "schedule", "config": {"cron": "0 9 * * MON"}}]}
    assert row({"flows": ["weekly"]})["next_run"] == "2026-10-12T09:00:00+00:00"
    monkeypatch.setattr(ventures.runner, "SCHEDULES_PAUSED", True)
    assert row({"flows": ["weekly"]})["next_run"] is None
