import logging

import audit_log
import runner
import store


def test_audit_store_is_created_lazily_under_glacier_home(tmp_path, monkeypatch):
    home = tmp_path / "not-created-yet"
    monkeypatch.setenv("GLACIER_HOME", str(home))

    assert not home.exists()
    audit_log.record("test.effect", what={"id": "one"})

    assert home.is_dir()
    assert len([event for event in audit_log.events(home=str(home)) if event["event_type"] == "test.effect"]) == 1


def test_unavailable_audit_store_does_not_change_runner_result(tmp_path, monkeypatch, caplog):
    home = tmp_path / "home"
    home.mkdir()
    (home / "audit.sqlite").mkdir()  # the audit store path is a folder, so writes fail
    monkeypatch.setenv("GLACIER_HOME", str(home))
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    monkeypatch.setattr(store, "set_run", lambda *args, **kwargs: None)
    caplog.set_level(logging.WARNING, logger="audit_log")

    result = runner.run_node("flow", "audit-unavailable", {
        "id": "cmd", "type": "command", "config": {"cmd": "echo ok"}
    }, None, str(tmp_path))

    assert result["state"] == "done"
    assert "Could not write audit event step.command_executed" in caplog.text
