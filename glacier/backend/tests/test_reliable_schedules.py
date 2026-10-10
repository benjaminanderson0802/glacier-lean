"""Acceptance cases for the durable schedule policies in PH12.3."""
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
import sys
import time

import schedule_policy
import store
import routes.home as home_routes


def test_missed_occurrences_collapse_to_one_on_startup():
    times = [
        datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
    ]
    assert schedule_policy.missed_run("run_once", times) == times[-1]


def test_missed_occurrences_can_be_skipped():
    assert schedule_policy.missed_run("skip", [datetime.now(timezone.utc)]) is None


def test_overlap_policy_never_admits_second_run():
    assert schedule_policy.overlap_action("queue", active=True) == "queue"
    assert schedule_policy.overlap_action("skip", active=True) == "skip"
    assert schedule_policy.overlap_action("queue", active=False) == "run"


def test_stuck_run_reason_is_plain_and_actionable():
    assert schedule_policy.stuck_reason("running", 90, 60) == "This run timed out after 1 minute."
    assert schedule_policy.stuck_reason("waiting", 90, 60) is None


def test_stale_run_times_out_with_reason_and_cannot_be_resurrected(tmp_path, monkeypatch):
    db = tmp_path / "health.sqlite"
    monkeypatch.setattr(store, "DB", str(db))
    store.init(str(db))
    graph = {"nodes": [{"id": "work", "type": "command"}], "edges": []}
    store.create_run("stale", "daily", graph)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE glacier_runs SET started_at='2026-10-08T00:00:00+00:00' WHERE run_id='stale'")
        connection.execute("UPDATE glacier_nodes SET state='running' WHERE run_id='stale'")
    changed = store.timeout_stuck_runs(60)
    assert changed == [{"run_id": "stale", "env_id": "daily", "reason": "This run timed out after 1 minute."}]
    assert store.get_run("stale")["status"] == "failed"
    assert store.get_run("stale")["outputs"]["work"] == changed[0]["reason"]
    store.set_run("stale", "done")
    assert store.get_run("stale")["status"] == "failed"


def test_health_counts_old_run_when_it_times_out(monkeypatch, tmp_path):
    old_cache = dict(home_routes._health_cache)
    monkeypatch.setattr(home_routes.store, "DB", str(tmp_path / "glacier.sqlite"))
    monkeypatch.setattr(home_routes.store, "timeout_stuck_runs", lambda: [])
    monkeypatch.setattr(home_routes.store, "list_runs", lambda _env: [
        {"run_id": "stale", "status": "failed", "started_at": "2026-10-08T00:00:00+00:00"},
    ])
    monkeypatch.setattr(home_routes.store, "get_run", lambda _run: {"waiting_on": "timeout:This run timed out after 24 hours."})
    monkeypatch.setattr(home_routes.vault, "read_note", lambda _path: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr(home_routes.vault, "write_note", lambda *_args, **_kwargs: "commit")
    home_routes._health_cache.update(at=0.0, report=None)
    try:
        report = home_routes._health_report()
        assert report["failed_runs"] == 0
        assert report["stuck_runs"] == 1
    finally:
        home_routes._health_cache.update(old_cache)


def test_home_publishes_next_run_and_daily_report_is_memory(server):
    flow = {"id": "health-scheduled", "name": "Health schedule", "nodes": [
        {"id": "timer", "type": "schedule", "config": {"cron": "0 9 * * *", "missed_run": "run_once", "overlap": "queue"}},
        {"id": "work", "type": "command", "config": {"cmd": "true"}},
    ], "edges": [{"id": "e", "source": "timer", "target": "work", "label": ""}]}
    server.put("/api/environments/health-scheduled", flow)
    body = server.get("/api/home")
    assert any(row["env_id"] == "health-scheduled" and row["next_run"] for row in body["next_runs"])
    assert set(body["health"]) >= {"failed_runs", "stuck_runs", "waiting_for_owner", "data_bytes", "note_path"}
    saved = server.get("/api/vault/note", params={"path": body["health"]["note_path"]})
    assert "# Glacier health" in saved["body"]


def test_schedule_keeps_firing_after_backend_restart(make_server):
    server = make_server().start()
    flow = {"id": "restart-schedule", "name": "Restart schedule", "nodes": [
        {"id": "timer", "type": "schedule", "config": {"cron": "*/2 * * * * *", "missed_run": "run_once"}},
        {"id": "work", "type": "command", "config": {"cmd": "echo tick"}},
    ], "edges": [{"id": "e", "source": "timer", "target": "work", "label": ""}]}
    server.put("/api/environments/restart-schedule", flow)
    deadline = time.time() + 30
    while time.time() < deadline:
        done = [row for row in server.get("/api/runs", params={"env_id": "restart-schedule"}) if row["status"] == "done"]
        if done:
            break
        time.sleep(0.25)
    assert done, "the schedule did not fire before restart"
    server.kill()
    server.start()
    deadline = time.time() + 30
    while time.time() < deadline:
        after = [row for row in server.get("/api/runs", params={"env_id": "restart-schedule"}) if row["status"] == "done"]
        if len(after) > len(done):
            break
        time.sleep(0.25)
    assert len(after) > len(done), "the persisted schedule did not fire after restart"


def test_pause_toggle_resumes_persisted_schedules_after_restart(make_server):
    server = make_server().start()
    flow = {"id": "paused-schedule", "name": "Paused schedule", "nodes": [
        {"id": "timer", "type": "schedule", "config": {"cron": "*/2 * * * * *"}},
        {"id": "work", "type": "command", "config": {"cmd": "echo tick"}},
    ], "edges": [{"id": "e", "source": "timer", "target": "work", "label": ""}]}
    server.put("/api/environments/paused-schedule", flow)
    assert server.post("/api/scheduler/pause-all")["paused"] is True
    server.kill()
    server.start()
    assert server.post("/api/scheduler/pause-all")["paused"] is False
    deadline = time.time() + 30
    while time.time() < deadline:
        runs = [row for row in server.get("/api/runs", params={"env_id": "paused-schedule"}) if row["status"] == "done"]
        if runs:
            break
        time.sleep(0.25)
    assert runs, "resuming after restart did not restart scheduled runs"


def test_overlapping_schedule_ticks_do_not_run_same_flow_together(server, tmp_path):
    marker = tmp_path / "active"
    overlap = tmp_path / "overlap"
    script = tmp_path / "work.py"
    script.write_text(
        "from pathlib import Path\nimport time\n"
        f"active = Path({str(marker)!r})\nconflict = Path({str(overlap)!r})\n"
        "if active.exists(): conflict.touch()\n"
        "active.touch()\ntime.sleep(2)\nactive.unlink(missing_ok=True)\n",
        encoding="utf-8",
    )
    command = f'"{sys.executable}" "{script}"'
    flow = {"id": "overlap-schedule", "name": "Overlap schedule", "nodes": [
        {"id": "timer", "type": "schedule", "config": {"cron": "* * * * * *", "overlap": "queue"}},
        {"id": "work", "type": "command", "config": {"cmd": command}},
    ], "edges": [{"id": "e", "source": "timer", "target": "work", "label": ""}]}
    server.put("/api/environments/overlap-schedule", flow)
    deadline = time.time() + 20
    while time.time() < deadline:
        runs = server.get("/api/runs", params={"env_id": "overlap-schedule"})
        if len(runs) >= 3 and all(row["status"] == "done" for row in runs[:2]):
            break
        time.sleep(0.25)
    assert len(runs) >= 3, "scheduled runs did not continue after a long run"
    assert not overlap.exists(), "two runs of the same flow overlapped"


def test_dev_logon_registration_is_current_user_only_and_does_not_repeat_instances():
    root = Path(__file__).resolve().parents[3]
    script = (root / "setup" / "register_dev_logon.ps1").read_text(encoding="utf-8")
    assert "New-ScheduledTaskTrigger -AtLogOn" in script
    assert "-MultipleInstances IgnoreNew" in script
    assert "RunLevel Highest" not in script
    assert "glacier-dev-run.ps1" in script
