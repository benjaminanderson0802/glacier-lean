import runner
import store


def test_tick_queued_before_the_schedule_was_removed_starts_nothing(monkeypatch):
    created = []
    monkeypatch.setattr(store, "create_run", lambda *args: created.append(args))
    monkeypatch.setattr(runner, "load_env", lambda env_id: {"id": env_id, "nodes": [{"id": "c", "type": "command"}], "edges": []})
    fn = getattr(runner.snapshot_scheduled_run, "__wrapped__", runner.snapshot_scheduled_run)
    assert fn("ticker", "run-late") is False
    assert created == []


def test_tick_with_schedule_still_present_creates_the_run(monkeypatch):
    created = []
    monkeypatch.setattr(store, "create_run", lambda *args: created.append(args))
    monkeypatch.setattr(runner, "load_env", lambda env_id: {"id": env_id, "nodes": [{"id": "s", "type": "schedule"}], "edges": []})
    fn = getattr(runner.snapshot_scheduled_run, "__wrapped__", runner.snapshot_scheduled_run)
    assert fn("ticker", "run-ok") is True
    assert created and created[0][0] == "run-ok"
