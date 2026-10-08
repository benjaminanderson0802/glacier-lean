"""Acceptance tests for Build teams: plans, role masks, durable task scheduling and proof."""
import json
import multiprocessing
import os
import subprocess
import threading
import time

import pytest

import teams


def _reserve_api_budget_in_child(home, results):
    os.environ["GLACIER_HOME"] = str(home)
    import routes.assistant_chat as assistant_chat
    try:
        assistant_chat._reserve_api_budget("openai", "x" * 1000, max_output_tokens=1200)
        results.put(True)
    except RuntimeError:
        results.put(False)


def _plan(mode="sequential", approvals=False):
    tasks = [
        {"id": "first", "title": "Create the result", "role": "builder", "depends_on": [],
         "acceptance": [{"kind": "command", "cmd": "test -f result.txt"}],
         "requires_approval": approvals},
        {"id": "second", "title": "Review the result", "role": "reviewer", "depends_on": ["first"],
         "acceptance": [{"kind": "command", "cmd": "grep -q approved result.txt"}]},
    ]
    return {"vision": {"goal": "Create an approved result", "done": ["result.txt contains approved"]},
            "spec": {"requirements": ["The system shall create result.txt"], "out_of_scope": [],
                     "acceptance": [{"kind": "command", "cmd": "test -f result.txt"}]},
            "features": [{"id": "result", "title": "Create approved result", "description": "Write result.txt"}],
            "harness": {"startup_script": "start.sh", "smoke_test": "smoke.sh", "checks": [],
                        "progress_log": "progress.md", "decision_log": "decisions.md"},
            "team": {"worker_mode": mode, "parallel_limit": 2,
                     "roles": [{"id": "builder", "charter": "Create files", "supervisor": "lead"},
                               {"id": "reviewer", "charter": "Review files", "supervisor": "lead"},
                               {"id": "lead", "charter": "Review handovers", "supervisor": None}],
                     "supervisor": "lead", "governor": "lead"}, "tasks": tasks,
            "guards": {"max_retries": 2, "task_timeout_seconds": 5}}


def test_team_plan_rejects_planner_as_task_or_supervisor():
    plan = _plan()
    plan["team"]["roles"].append({"id": "planner", "charter": "Plan", "supervisor": "lead"})
    plan["tasks"][0]["role"] = "planner"
    with pytest.raises(ValueError, match="planner"):
        teams.validate_plan(plan)


def test_planner_schema_is_accepted_by_codex_strict_structured_output(monkeypatch):
    import assistant

    captured = {}
    plan = _plan()
    vision = plan.pop("vision")

    def answer(_prompt, schema):
        captured["schema"] = schema
        return plan

    monkeypatch.setattr(assistant, "_ask_codex", answer)
    teams.plan_team(vision, engine="codex")

    schema = captured["schema"]

    def check_strict_objects(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
                assert set(value.get("required", [])) == set(value.get("properties", {}))
            for nested in value.values():
                check_strict_objects(nested)
        elif isinstance(value, list):
            for nested in value:
                check_strict_objects(nested)

    check_strict_objects(schema)


def test_mask_contains_role_task_and_only_relevant_memory():
    task = dict(_plan()["tasks"][0], description="use relevant information")
    context = teams.task_context(_plan()["team"]["roles"][0], task,
                                 [{"path": "a.md", "body": "relevant needle"},
                                  {"path": "b.md", "body": "irrelevant haystack"}])
    assert "Create files" in context and "Create the result" in context
    assert "relevant needle" in context and "irrelevant haystack" not in context


@pytest.mark.parametrize("mode,limit,expected_max", [("sequential", 4, 1), ("parallel", 2, 2)])
def test_scheduler_respects_mode_limit(mode, limit, expected_max):
    plan = _plan(mode)
    plan["team"]["parallel_limit"] = limit
    plan["tasks"].append({"id": "parallel", "title": "Independent", "role": "builder", "depends_on": [],
                          "acceptance": [{"kind": "command", "cmd": "true"}]})
    active = teams.ready_batch(plan, {"first": "pending", "second": "pending", "parallel": "pending"}, limit_override=limit)
    assert len(active) == expected_max


def test_dependencies_and_approval_pause_only_its_branch():
    plan = _plan(approvals=True)
    plan["team"]["worker_mode"] = "parallel"
    plan["tasks"].append({"id": "independent", "title": "Do unrelated work", "role": "builder",
                          "depends_on": [], "acceptance": [{"kind": "command", "cmd": "true"}]})
    states = {task["id"]: "pending" for task in plan["tasks"]}
    assert {t["id"] for t in teams.ready_batch(plan, states)} == {"first", "independent"}
    states["first"] = "awaiting_approval"
    assert {t["id"] for t in teams.ready_batch(plan, states)} == {"independent"}


def test_bad_handover_is_rejected_and_task_is_runnable_again(monkeypatch):
    calls = []
    monkeypatch.setattr(teams, "_worker", lambda *args: calls.append(args) or {"output": "bad", "exit_code": 0})
    monkeypatch.setattr(teams, "_review", lambda *args: {"passed": False, "evidence": "missing result"})
    result = teams.execute_task("t", "first", _plan(), _plan()["tasks"][0], "/tmp", {}, attempt=1)
    assert result["status"] == "retry" and calls


def test_stuck_task_files_claim(monkeypatch):
    captured = []
    monkeypatch.setattr(teams.claims, "file_claim", lambda *a, **kw: captured.append((a, kw)) or {"id": "claim-1"})
    result = teams.stuck_claim("run1", "task1", 2, "same failure")
    assert result == "claim-1" and captured


def test_full_plan_reaches_done_with_stand_in_workers(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import vault
    vault.init(str(tmp_path / "vault"))
    plan = _plan()
    def worker(context, workspace, task):
        if task["id"] == "first":
            (tmp_path / "result.txt").write_text("approved\n")
        return {"output": "completed", "exit_code": 0}
    monkeypatch.setattr(teams, "_worker", worker)
    monkeypatch.setattr(teams, "_review", lambda *a: {"passed": True, "evidence": "reviewed"})
    monkeypatch.setattr(teams, "_check_task", lambda *a: {"passed": True, "evidence": "check passed"})
    monkeypatch.setattr(teams, "_govern", lambda *a: {"passed": True, "evidence": "vision met"})
    monkeypatch.setattr(teams, "_objective_check", lambda *a: {"passed": True, "evidence": "spec passed"})
    state = teams.run_team_local("team1", plan, str(tmp_path))
    assert state["status"] == "done"
    assert all(task["status"] == "done" for task in state["tasks"].values())


def test_task_context_is_rebuilt_for_each_task():
    first = teams.task_context({"id": "builder", "charter": "write"}, {"id": "a", "title": "A", "acceptance": []}, [])
    second = teams.task_context({"id": "reviewer", "charter": "review"}, {"id": "b", "title": "B", "acceptance": []}, [])
    assert "write" not in second and "Charter: review" in second and "Task: A" not in second


def test_resume_skips_finished_tasks(tmp_path, monkeypatch):
    calls = []
    governed = []
    monkeypatch.setattr(teams, "_worker", lambda context, workspace, task: calls.append(task["id"]) or
                        {"output": "ok", "exit_code": 0})
    monkeypatch.setattr(teams, "_review", lambda *a: {"passed": True, "evidence": "reviewed"})
    monkeypatch.setattr(teams, "_check_task", lambda *a: {"passed": True, "evidence": "passed"})
    # Stand-in governor, like the other team tests: no real model endpoint is reachable in CI.
    monkeypatch.setattr(teams, "_govern", lambda *a: governed.append(True) or {"passed": True, "evidence": "vision met"})
    monkeypatch.setattr(teams, "_objective_check", lambda *a: {"passed": True, "evidence": "spec passed"})
    plan = _plan()
    state = {"status": "running", "tasks": {"first": {"status": "done", "attempts": 1},
                                               "second": {"status": "pending", "attempts": 0}}}
    result = teams.run_team_local("resume", plan, str(tmp_path), state=state)
    assert calls == ["second"] and result["status"] == "done"
    assert governed, "the resumed team still reaches the governor's final check"


@pytest.mark.parametrize("engine", ["codex", "claude", "gemini", "openai", "anthropic", "local"])
def test_plan_team_uses_selected_ask_engine(engine, monkeypatch):
    import routes.assistant_chat as assistant_chat
    seen = []
    response = {key: value for key, value in _plan().items() if key != "vision"}
    monkeypatch.setattr(teams, "ask_engine", lambda prompt, route, schema=None: seen.append((route, schema)) or response)
    plan = teams.plan_team(_plan()["vision"], engine)
    assert plan["team"]["engine"] == engine
    assert seen and seen[0][0] == engine
    assert plan["team"]["worker_mode"] == ("sequential" if engine == "local" else "parallel")
    if engine != "local":
        assert 3 <= plan["team"]["parallel_limit"] <= 5


@pytest.mark.parametrize("engine", ["codex", "claude", "gemini", "openai", "anthropic", "local"])
def test_build_interview_accepts_each_ask_engine(monkeypatch, engine):
    import routes.assistant_chat as assistant_chat
    import routes.teams as team_routes
    seen = []
    monkeypatch.setattr(teams, "ask_engine", lambda prompt, route, schema=None: seen.append(route) or {
        "reply": "What should the finished project do?", "automation": False})
    monkeypatch.setattr(assistant_chat, "_conversation_id", lambda value: value)
    monkeypatch.setattr(assistant_chat, "_conversation_context", lambda value: "")
    monkeypatch.setattr(assistant_chat, "_with_conversation_context", lambda message, context: message)
    monkeypatch.setattr(assistant_chat, "_append_conversation", lambda *args: None)
    monkeypatch.setattr(assistant_chat, "_conversation_path", lambda value: "interviews/test.md")
    result = team_routes.interview(team_routes.InterviewTurn(message="Build a project", engine=engine))
    assert result["reply"] == "What should the finished project do?"
    assert seen == [engine]


def test_team_control_actions_are_audited(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    teams.init(str(tmp_path / "glacier.sqlite"))
    import audit_log
    import vault
    vault.init(str(tmp_path / "vault"))
    vision = teams.create_vision({"goal": "Build", "done": ["works"]})
    saved = teams.save_plan(_plan(), vision["path"])
    events = []
    monkeypatch.setattr(audit_log, "record", lambda event, **kwargs: events.append((event, kwargs)))
    monkeypatch.setattr(teams.DBOS, "start_workflow", lambda *args: None)
    monkeypatch.setattr(teams.DBOS, "send", lambda *args, **kwargs: None)
    teams._save(saved["team_id"], status="running")
    teams.control(saved["team_id"], "pause")
    teams.control(saved["team_id"], "resume")
    teams.control(saved["team_id"], "stop")
    assert [event for event, _ in events] == ["team.paused", "team.resumed", "team.stopped"]


def test_pause_finishes_active_task_and_starts_nothing_new(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import vault
    vault.init(str(tmp_path / "vault"))
    plan = _plan()
    vision = teams.create_vision(plan["vision"])
    saved = teams.save_plan(plan, vision["path"], str(tmp_path / "workspace"))
    teams._save(saved["team_id"], status="running")
    entered, release = threading.Event(), threading.Event()
    calls = []

    def worker(context, workspace, task):
        calls.append(task["id"])
        entered.set()
        assert release.wait(5)
        return {"output": "finished", "exit_code": 0}

    monkeypatch.setattr(teams, "_worker", worker)
    monkeypatch.setattr(teams, "_review", lambda *a: {"passed": True, "evidence": "reviewed"})
    monkeypatch.setattr(teams, "_check_task", lambda *a: {"passed": True, "evidence": "passed"})
    result = {}
    thread = threading.Thread(target=lambda: result.update(teams.run_team_local(saved["team_id"], plan,
        str(tmp_path / "workspace"), state=teams.get(saved["team_id"]))))
    thread.start()
    assert entered.wait(5)
    assert teams.control(saved["team_id"], "pause")["status"] == "pausing"
    release.set()
    thread.join(5)

    assert not thread.is_alive()
    assert calls == ["first"]
    assert result["status"] == "paused"
    assert teams.get(saved["team_id"])["tasks"]["first"]["status"] == "done"
    assert "Task first: done" in teams.get(saved["team_id"])["progress_log"]


def test_stop_terminates_running_worker_and_keeps_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import vault
    vault.init(str(tmp_path / "vault"))
    vision = teams.create_vision({"goal": "Build", "done": ["works"]})
    saved = teams.save_plan(_plan(), vision["path"])
    teams._save(saved["team_id"], status="running")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    process = subprocess.Popen(["sleep", "30"], start_new_session=True)
    teams._register_worker_process(saved["team_id"], "first", process)

    result = teams.control(saved["team_id"], "stop")

    assert result["status"] == "stopped"
    assert process.poll() is not None
    assert worktree.is_dir()
    assert teams.get(saved["team_id"])["status"] == "stopped"


@pytest.mark.parametrize("engine", ["claude", "gemini", "openai", "anthropic", "local"])
def test_api_team_worker_uses_fake_engine_and_applies_only_checked_patch(tmp_path, monkeypatch, engine):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    (workspace / "result.txt").write_text("before\n")
    patch = """diff --git a/result.txt b/result.txt
index 3f4c56d..d5c6e76 100644
--- a/result.txt
+++ b/result.txt
@@ -1 +1 @@
-before
+after
"""
    seen = []
    monkeypatch.setattr(teams, "_engine_call_override", lambda prompt, engine: seen.append(engine) or {"reply": patch})
    result = teams._worker_patch("task context", str(workspace), {"id": "task", "title": "Update result",
                                    "engine": engine, "timeout_seconds": 5}, engine)
    assert seen == [engine]
    assert result["exit_code"] == 0
    assert (workspace / "result.txt").read_text() == "after\n"


@pytest.mark.skipif(os.name == "nt", reason="the process-lock race check uses fork")
def test_parallel_api_workers_reserve_monthly_budget_across_processes(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    (tmp_path / "settings.json").write_text(json.dumps({
        "openai_monthly_cap_usd": 3.0,
        "openai_input_usd_per_million": 1000.0,
        "openai_output_usd_per_million": 1000.0,
    }))
    context = multiprocessing.get_context("fork")
    results = context.Queue()
    workers = [context.Process(target=_reserve_api_budget_in_child, args=(tmp_path, results)) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(5)
    assert all(not worker.is_alive() and worker.exitcode == 0 for worker in workers)
    accepted = [results.get(timeout=1) for _ in workers]
    assert sum(accepted) == 1
    import routes.assistant_chat as assistant_chat
    assert assistant_chat._monthly_api_spend("openai") == 2.2


def test_resume_honors_legacy_done_and_requires_evaluator_for_new_work(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(teams, "_worker", lambda context, workspace, task: calls.append(task["id"]) or
                        {"output": "ok", "exit_code": 0})
    monkeypatch.setattr(teams, "_review", lambda *a: {"passed": True, "evidence": "reviewed"})
    monkeypatch.setattr(teams, "_check_task", lambda *a: {"passed": True, "evidence": "passed"})
    monkeypatch.setattr(teams, "_govern", lambda *a: {"passed": True, "evidence": "vision met"})
    monkeypatch.setattr(teams, "_objective_check", lambda *a: {"passed": True, "evidence": "spec passed"})
    plan = _plan()
    plan["team"]["roles"].append({"id": "evaluator", "charter": "Grade the feature independently",
                                    "supervisor": "lead"})
    plan["tasks"][0]["feature_id"] = "result"
    plan["tasks"][1]["feature_id"] = "result"
    plan["tasks"][1]["contract"] = {"pass_criteria": ["result exists"]}
    plan["tasks"].append({"id": "evaluate", "title": "Evaluate the result", "role": "evaluator",
                          "feature_id": "result", "depends_on": ["second"],
                          "acceptance": [{"kind": "command", "cmd": "test -f result.txt"}]})
    state = {"status": "running", "tasks": {
        "first": {"status": "done", "attempts": 1},
        "second": {"status": "pending", "attempts": 0},
        "evaluate": {"status": "pending", "attempts": 0}},
        "features": {"result": {"status": "passing",
                                  "evaluator_evidence": "legacy completed task records; final objective check required"}}}

    result = teams.run_team_local("legacy-resume", plan, str(tmp_path), state=state)

    assert calls == ["second", "evaluate"]
    assert result["tasks"]["first"]["legacy_note"] == "legacy: finished before evaluator grading"
    assert "legacy: finished before evaluator grading: task first" in result["progress_log"]
    assert result["features"]["result"]["status"] == "passing"
    assert result["features"]["result"]["evaluator_evidence"]
    assert result["status"] == "done"


def test_team_api_saves_approved_plan_and_home_summary(server):
    vision = server.post("/api/build/vision", {"vision": {"goal": "Create an approved result",
                                                           "done": ["result.txt contains approved"]}})
    assert vision["confirmed"] and vision["path"].startswith("visions/")
    plan = _plan()
    saved = server.post("/api/teams", {"plan": plan, "vision_path": vision["path"]})
    assert saved["approved"] is True
    detail = server.get(f"/api/teams/{saved['team_id']}")
    assert detail["status"] == "approved" and detail["plan"]["vision"]["goal"] == plan["vision"]["goal"]
    assert isinstance(server.get("/api/home")["teams_running"], list)


def test_worker_cannot_edit_feature_list_or_mark_passing(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import vault
    vault.init(str(tmp_path / "vault"))
    vision = teams.create_vision({"goal": "Build", "done": ["works"]})
    saved = teams.save_plan(_plan(), vision["path"])
    with pytest.raises(ValueError, match="only the evaluator"):
        teams.update_feature(saved["team_id"], "result", "passing", "looks good", "builder")
    state = teams.get(saved["team_id"])
    assert state["features"]["result"]["status"] == "pending"


def test_only_evaluator_pass_with_evidence_flips_feature_status(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    import vault
    vault.init(str(tmp_path / "vault"))
    vision = teams.create_vision({"goal": "Build", "done": ["works"]})
    saved = teams.save_plan(_plan(), vision["path"])
    with pytest.raises(ValueError, match="evidence"):
        teams.update_feature(saved["team_id"], "result", "passing", "", "evaluator")
    result = teams.update_feature(saved["team_id"], "result", "passing", "acceptance passed", "evaluator")
    assert result["status"] == "passing"


def test_contract_must_exist_before_builder_context():
    with pytest.raises(ValueError, match="contract must exist"):
        teams.build_context({"id": "builder", "charter": "build"},
                            {"id": "f", "title": "feature"}, {}, "progress")


def test_attempt_limit_resets_then_replans_then_files_claim():
    first = teams.stall_transition(3, 0, "attempts failed")
    second = teams.stall_transition(3, first["replans"], "smaller plan failed")
    third = teams.stall_transition(3, second["replans"], "second plan failed")
    assert first["action"] == second["action"] == "reset_and_replan"
    assert first["handoff_note"] == "attempts failed"
    assert third["action"] == "claim" and third["evidence"] == "second plan failed"


def test_final_objective_check_blocks_done_when_spec_acceptance_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    plan = _plan()
    plan["spec"]["acceptance"] = [{"kind": "command", "cmd": "test -f missing.txt"}]
    monkeypatch.setattr(teams, "_worker", lambda *args: {"output": "completed", "exit_code": 0})
    monkeypatch.setattr(teams, "_review", lambda *args: {"passed": True, "evidence": "reviewed"})
    monkeypatch.setattr(teams, "_check_task", lambda *args: {"passed": True, "evidence": "passed"})
    monkeypatch.setattr(teams, "_govern", lambda *args: {"passed": True, "evidence": "vision met"})
    result = teams.run_team_local("team-objective", plan, str(tmp_path), state={
        "status": "running", "tasks": {"first": {"status": "done", "attempts": 1},
                                          "second": {"status": "done", "attempts": 1}},
        "features": {"result": {"status": "passing", "evaluator_evidence": "verified"}}})
    assert result["status"] == "needs_owner"
    assert result["objective_check"]["passed"] is False
