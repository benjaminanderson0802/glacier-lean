"""Independent PH1 acceptance checks for command effects and audit durability.

These checks specify what a runtime audit must prove at each side-effect boundary.
They intentionally do not patch audit recording or inspect builder-only helpers.
"""
import json
import shlex
import sys

import pytest

import audit_log
import runner
import store


@pytest.fixture
def audit_case(tmp_path, monkeypatch):
    home = tmp_path / "glacier-home"
    work = tmp_path / "workspace"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("GLACIER_HOME", str(home))
    monkeypatch.setattr(store, "graph_of", lambda _: {})
    monkeypatch.setattr(store, "get_run", lambda _: {"author": "audit-boundary-test"})
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    return {"home": home, "work": work, "tmp": tmp_path}


def _command(case, source, *args):
    """Create a local command whose only writes are explicit files under tmp_path."""
    script = case["tmp"] / f"command-{len(list(case['tmp'].glob('command-*.py')))}.py"
    script.write_text(source, encoding="utf-8")
    return " ".join([shlex.quote(sys.executable), shlex.quote(str(script)),
                     *(shlex.quote(str(arg)) for arg in args)])


def _events_for(run_id, node_id):
    return [event for event in audit_log.events()
            if event["what"].get("run_id") == run_id
            and event["what"].get("node_id") == node_id]


def _node(command, *, retries=0, timeout=5):
    return {"id": "effect", "type": "command", "config": {
        "cmd": command, "retries": retries, "timeout": timeout,
    }}


@pytest.mark.parametrize(("exit_code", "expected_state"), [(0, "done"), (7, "failed")])
def test_command_start_and_known_outcome_are_durably_correlated(
        audit_case, exit_code, expected_state):
    run_id = f"known-outcome-{exit_code}"
    probe = audit_case["tmp"] / f"start-probe-{exit_code}.json"
    effect = audit_case["tmp"] / f"effect-{exit_code}.txt"
    script = r'''
import json, pathlib, sqlite3, sys
home, probe, effect, code = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), int(sys.argv[4])
db = pathlib.Path(home) / "audit.sqlite"
starts = []
if db.exists() and db.is_file():
    with sqlite3.connect(db) as connection:
        try:
            rows = connection.execute("SELECT event_type, what FROM glacier_audit").fetchall()
            starts = [json.loads(payload) for event, payload in rows if event == "step.command_started"]
        except sqlite3.OperationalError:
            pass
probe.write_text(json.dumps(starts), encoding="utf-8")
effect.write_text("attempted", encoding="utf-8")
raise SystemExit(code)
'''
    command = _command(audit_case, script, audit_case["home"], probe, effect, exit_code)

    result = runner._run_node_impl("audit-flow", run_id, _node(command), None,
                                   str(audit_case["work"]))

    assert effect.read_text(encoding="utf-8") == "attempted"
    starts_seen_by_command = json.loads(probe.read_text(encoding="utf-8"))
    assert any(row.get("env_id") == "audit-flow" and row.get("run_id") == run_id
               and row.get("node_id") == "effect" and row.get("attempt") == 1
               for row in starts_seen_by_command), "the side effect began before a durable start record"
    assert result["state"] == expected_state
    records = _events_for(run_id, "effect")
    started = [event for event in records if event["event_type"] == "step.command_started"]
    completed = [event for event in records if event["event_type"] == "step.command_executed"]
    assert len(started) == len(completed) == 1
    assert completed[0]["what"].get("attempt") == 1
    assert completed[0]["what"].get("exit_code") == exit_code


def test_each_retry_attempt_has_a_start_and_known_outcome(audit_case):
    run_id = "retry-boundaries"
    marks = audit_case["tmp"] / "retry-count"
    script = r'''
import pathlib, sys
marks = pathlib.Path(sys.argv[1])
count = int(marks.read_text()) + 1 if marks.exists() else 1
marks.write_text(str(count))
raise SystemExit(1 if count == 1 else 0)
'''
    command = _command(audit_case, script, marks)

    result = runner._run_node_impl("audit-flow", run_id, _node(command, retries=1), None,
                                   str(audit_case["work"]))

    assert marks.read_text() == "2"
    assert result["state"] == "done"
    records = _events_for(run_id, "effect")
    starts = [event for event in records if event["event_type"] == "step.command_started"]
    outcomes = [event for event in records if event["event_type"] == "step.command_executed"]
    assert [event["what"].get("attempt") for event in starts] == [1, 2]
    assert [event["what"].get("attempt") for event in outcomes] == [1, 2]
    assert [event["what"].get("exit_code") for event in outcomes] == [1, 0]


def test_interruption_after_effect_is_explicitly_unknown_or_interrupted(audit_case, monkeypatch):
    run_id = "interrupted-boundary"
    effect = audit_case["tmp"] / "effect-before-interruption"
    script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('done')"
    command = _command(audit_case, script, effect)
    actual_run_command = runner.run_command

    def interrupt_after_effect(cfg, timeout, ws, sandbox=False):
        actual_run_command(cfg, timeout, ws, sandbox)
        raise KeyboardInterrupt("simulated runner interruption after external effect")

    monkeypatch.setattr(runner, "run_command", interrupt_after_effect)
    with pytest.raises(KeyboardInterrupt):
        runner._run_node_impl("audit-flow", run_id, _node(command), None,
                              str(audit_case["work"]))

    assert effect.read_text(encoding="utf-8") == "done"
    records = _events_for(run_id, "effect")
    assert any(event["event_type"] == "step.command_started" for event in records)
    assert any(event["what"].get("outcome") in {"interrupted", "unknown"}
               for event in records), "a started effect with no completion needs an explicit unresolved state"


def test_unavailable_audit_storage_cannot_be_reported_as_fully_audited_success(
        audit_case, monkeypatch, caplog):
    home = audit_case["tmp"] / "unavailable-home"
    home.mkdir()
    (home / "audit.sqlite").mkdir()
    monkeypatch.setenv("GLACIER_HOME", str(home))
    effect = audit_case["tmp"] / "effect-without-store"
    command = _command(audit_case,
                       "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('done')", effect)

    result = runner._run_node_impl("audit-flow", "unavailable-storage", _node(command), None,
                                   str(audit_case["work"]))

    assert effect.read_text(encoding="utf-8") == "done"
    assert "Could not write audit event" in caplog.text
    assert result.get("audit_state") in {"unavailable", "incomplete"} or result["state"] != "done", (
        "the command succeeded but the runtime result does not expose that its audit record was lost"
    )
