"""Builder unit regressions for PH1 event placement, not phase acceptance."""
import json

import pytest

import audit_log
import runner
import store


@pytest.fixture
def runtime_records(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    monkeypatch.setattr(store, "graph_of", lambda _: {})
    monkeypatch.setattr(store, "get_run", lambda _: {"author": "owner"})
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    return tmp_path


@pytest.mark.parametrize("succeed_at", [2, 9])
def test_command_attempt_effects_each_have_an_audit_row(runtime_records, succeed_at):
    marks = runtime_records / "attempts"
    result = runner._run_node_impl("flow", "run", {
        "id": "command", "type": "command", "config": {
            "cmd": f'echo tick >> "{marks}"; [ $(wc -l < "{marks}") -ge {succeed_at} ]',
            "retries": 1,
        },
    }, None)

    assert marks.read_text().splitlines() == ["tick", "tick"]
    assert result["state"] == ("done" if succeed_at == 2 else "failed")
    rows = audit_log.events("step.command_executed")
    assert len(rows) == 2
    assert [row["what"]["attempt"] for row in rows] == [1, 2]
    assert [row["what"]["exit_code"] for row in rows] == [1, 0 if succeed_at == 2 else 1]
    assert all(row["who"] == "owner" for row in rows)
    assert str(marks) not in json.dumps(rows)  # commands and their contents stay out of the audit


def test_child_start_records_one_effect(runtime_records, monkeypatch):
    monkeypatch.setattr(runner, "load_env", lambda _: {"nodes": []})
    monkeypatch.setattr(store, "create_run", lambda *args: None)

    assert runner.start_child("parent", "run", "node", "child", "child-run", 0)["state"] == "running"

    rows = audit_log.events("run.child_started")
    assert len(rows) == 1
    assert rows[0]["what"]["run_id"] == "child-run"
    assert rows[0]["what"]["parent_run_id"] == "run"


@pytest.mark.parametrize("reserved", [True, False])
def test_schedule_start_records_only_reserved_run(runtime_records, monkeypatch, reserved):
    monkeypatch.setattr(runner, "load_env", lambda _: {"nodes": [{"type": "schedule"}]})
    monkeypatch.setattr(store, "create_run", lambda *args: reserved)

    assert runner.snapshot_scheduled_run("scheduled", "run") is reserved

    rows = audit_log.events("run.started")
    assert len(rows) == int(reserved)
    if reserved:
        assert rows[0]["what"] == {"env_id": "scheduled", "run_id": "run", "source": "schedule"}
