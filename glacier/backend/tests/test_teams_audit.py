"""Build API effects leave safe audit records without storing prompt contents."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _plan():
    return {
        "vision": {"goal": "Build a tiny local tool", "done": ["The proof step is defined"]},
        "spec": {"requirements": ["The system shall run locally"], "out_of_scope": [],
                 "acceptance": ["WHEN started, THE system SHALL finish the proof step"]},
        "features": [{"id": "proof", "title": "Proof step", "description": "One bounded step",
                      "acceptance": ["The proof step is defined"]}],
        "harness": {"startup_script": "start.sh", "smoke_test": "smoke.sh", "checks": [],
                    "progress_log": "progress.md", "decision_log": "decisions.md"},
        "team": {"worker_mode": "sequential", "parallel_limit": 1,
                 "roles": [{"id": "lead", "charter": "Coordinate the proof", "supervisor": None}],
                 "supervisor": "lead", "governor": "lead"},
        "tasks": [{"id": "proof", "title": "Check the proof step", "role": "lead", "depends_on": [],
                   "acceptance": [{"kind": "command", "cmd": "true"}]}],
        "guards": {"max_retries": 1, "task_timeout_seconds": 30},
    }


def test_build_http_effects_are_audited_once_without_prompt_text(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import audit_log
    import assistant
    import teams
    import vault
    from routes import teams as route

    vault.init(str(tmp_path / "vault"))
    teams.init(str(tmp_path / "glacier.sqlite"))
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app)
    monkeypatch.setattr(assistant, "_ask_codex", lambda *_: {
        "reply": "What should the proof step check?", "automation": False})
    interview = client.post("/api/build/interview", json={
        "conversation_id": "1" * 36, "message": "Test-specific private interview prompt", "engine": "codex"})
    assert interview.status_code == 200

    vision = client.post("/api/build/vision", json={"vision": _plan()["vision"]})
    assert vision.status_code == 200
    spec = client.post("/api/build/spec", json={"spec": _plan()["spec"]})
    assert spec.status_code == 200
    monkeypatch.setattr(teams, "plan_team", lambda *_: _plan())
    proposed = client.post("/api/build/plan", json={"vision_path": vision.json()["path"], "engine": "codex"})
    assert proposed.status_code == 200
    saved = client.post("/api/teams", json={"plan": proposed.json()["plan"], "vision_path": vision.json()["path"]})
    assert saved.status_code == 200
    monkeypatch.setattr(teams.DBOS, "start_workflow", lambda *args: None)
    monkeypatch.setattr(teams.DBOS, "send", lambda *args, **kwargs: None)
    started = client.post(f"/api/teams/{saved.json()['team_id']}/run")
    assert started.status_code == 200
    team_id = saved.json()["team_id"]
    paused = client.post(f"/api/teams/{team_id}/pause")
    assert paused.status_code == 200 and paused.json()["status"] == "pausing"
    stopped = client.post(f"/api/teams/{team_id}/stop")
    assert stopped.status_code == 200 and stopped.json()["status"] == "stopping"

    rows = audit_log.events(home=str(tmp_path))
    kinds = [row["event_type"] for row in rows]
    expected = ["build.interview_turn", "build.vision_confirmed", "build.spec_approved",
                "build.plan_requested", "team.plan_approved", "team.run_started",
                "team.pause_requested", "team.stop_requested"]
    for event in expected:
        assert kinds.count(event) == 1
    assert "Test-specific private interview prompt" not in json.dumps(rows)


def test_live_team_controls_are_requested_at_safe_points(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import teams
    import vault

    vault.init(str(tmp_path / "vault"))
    teams.init(str(tmp_path / "glacier.sqlite"))
    vision = teams.create_vision(_plan()["vision"])
    saved = teams.save_plan(_plan(), vision["path"])
    row = teams._read(saved["team_id"])
    state = row["state"]
    state["workflow_started"] = True
    monkeypatch.setattr(teams.DBOS, "send", lambda *args, **kwargs: None)
    teams._save(saved["team_id"], status="running", state=state)

    assert teams.pause(saved["team_id"])["status"] == "pausing"
    assert teams._read(saved["team_id"])["state"]["control_request"] == "pause"
    assert teams.stop(saved["team_id"])["status"] == "stopping"
    assert teams._read(saved["team_id"])["state"]["control_request"] == "stop"
