"""Durable, verified Build teams. Plans and visions are plain notes; SQLite is a rebuildable run index."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import sqlite3
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from dbos import DBOS, SetWorkflowID

import claims
import memory_context
import runner
import store
import vault
import verify
import audit_log

PLANNER_IDS = {"planner", "the-planner"}
DB = ""
_worker_processes: dict[tuple[str, str], object] = {}
_worker_process_lock = threading.RLock()
_team_state_lock = threading.RLock()
_engine_call_override = None
ASK_ENGINES = {"codex", "claude", "gemini", "openai", "anthropic", "local"}


def init(path: str | None = None) -> None:
    global DB
    DB = path or os.path.join(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), "glacier.sqlite")
    os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS glacier_teams(
            team_id TEXT PRIMARY KEY, status TEXT NOT NULL, vision_path TEXT NOT NULL,
            plan TEXT NOT NULL, state TEXT NOT NULL, workspace TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")


def _conn():
    if not DB:
        init()
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _forbid_planner(value: str, where: str) -> None:
    if str(value or "").strip().casefold() in PLANNER_IDS:
        raise ValueError(f"planner cannot be a team member or {where}")


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict) or not isinstance(plan.get("vision"), dict):
        raise ValueError("plan needs a vision")
    if not isinstance(plan.get("spec"), dict):
        # Compatibility for the original card API: the Vision is the approved spec.
        plan["spec"] = {"requirements": [], "out_of_scope": [],
                        "acceptance": plan["vision"].get("done", [])}
    spec = plan["spec"]
    if not isinstance(spec.get("requirements", []), list) or not isinstance(spec.get("out_of_scope", []), list) or not isinstance(spec.get("acceptance", []), list):
        raise ValueError("Spec requirements, out_of_scope and acceptance must be lists")
    features = plan.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("plan needs a structured feature list")
    feature_ids = set()
    for feature in features:
        if not isinstance(feature, dict) or not feature.get("id") or not feature.get("title"):
            raise ValueError("each feature needs an id and title")
        if feature["id"] in feature_ids:
            raise ValueError("feature ids must be unique")
        feature_ids.add(feature["id"])
        if feature.get("status", "pending") not in ("pending", "in_progress", "passing"):
            raise ValueError("invalid feature status")
        # Input cannot assert evaluator authority. New features always begin pending.
        feature["status"] = "pending"
    team, tasks = plan.get("team"), plan.get("tasks")
    if not isinstance(team, dict) or not isinstance(team.get("roles"), list) or not team["roles"]:
        raise ValueError("team needs roles")
    if team.get("worker_mode") not in ("sequential", "parallel"):
        raise ValueError("worker_mode must be sequential or parallel")
    limit = team.get("parallel_limit", 1)
    if not isinstance(limit, int) or limit < 1 or limit > 32:
        raise ValueError("parallel_limit must be between 1 and 32")
    engine = team.get("engine")
    if engine and engine not in ASK_ENGINES:
        raise ValueError("team engine is not supported")
    if engine == "local" and (team.get("worker_mode") != "sequential" or limit != 1):
        raise ValueError("local teams run one worker at a time")
    if engine in ASK_ENGINES - {"local"} and (team.get("worker_mode") != "parallel" or not 3 <= limit <= 5):
        raise ValueError("subscription and API teams need 3 to 5 parallel workers")
    roles = {}
    for role in team["roles"]:
        if not isinstance(role, dict) or not role.get("id") or not role.get("charter"):
            raise ValueError("each role needs an id and charter")
        rid = str(role["id"])
        _forbid_planner(rid, "team role")
        if rid in roles:
            raise ValueError("role ids must be unique")
        roles[rid] = role
        _forbid_planner(role.get("supervisor"), "supervisor")
    for key in ("supervisor", "governor"):
        if team.get(key):
            _forbid_planner(team[key], key)
            if team[key] not in roles:
                raise ValueError(f"{key} must name a team role")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("plan needs tasks")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or not task.get("id") or not task.get("title"):
            raise ValueError("each task needs an id and title")
        tid = str(task["id"])
        if tid in ids:
            raise ValueError("task ids must be unique")
        ids.add(tid)
        _forbid_planner(task.get("role"), "task role")
        if task.get("role") not in roles:
            raise ValueError(f"task {tid} names an unknown role")
        checks = task.get("acceptance")
        if not isinstance(checks, list) or not checks:
            raise ValueError(f"task {tid} needs acceptance checks")
        verify.validate(checks)
        if not isinstance(task.get("depends_on", []), list):
            raise ValueError(f"task {tid} dependencies must be a list")
    if any(dep not in ids or dep == task["id"] for task in tasks for dep in task.get("depends_on", [])):
        raise ValueError("task dependencies must reference other tasks")
    guards = plan.get("guards") or {}
    if not 1 <= int(guards.get("max_retries", 2)) <= 3:
        raise ValueError("max_retries must be between 1 and 3")
    if not 1 <= int(guards.get("task_timeout_seconds", 1800)) <= 14400:
        raise ValueError("task time limit must be between 1 and 14400 seconds")
    return plan


def task_context(role: dict, task: dict, memory: list[dict], vision: dict | None = None) -> str:
    """Construct a fresh, task-scoped mask. No conversation or previous worker output is included."""
    terms = {word.casefold() for word in re.findall(r"[A-Za-z0-9]{3,}", " ".join(
        (task.get("title", ""), task.get("description", ""), role.get("charter", ""))))}
    selected = [item for item in memory if not terms or terms.intersection(
        word.casefold() for word in re.findall(r"[A-Za-z0-9]{3,}", str(item.get("body", ""))))]
    return ("You are working under this role mask. Follow only this charter for this task.\n"
            f"Role: {role['id']}\nCharter: {role['charter']}\n"
            "Vision reference:\n" + json.dumps(vision or {}, ensure_ascii=False) + "\n"
            f"Task: {task['title']}\nDetails: {task.get('description', '')}\n"
            "Acceptance checks (independent):\n" + json.dumps(task.get("acceptance", []), ensure_ascii=False) +
            "\nRelevant memory:\n" + "\n".join(f"[{item.get('path', '')}] {item.get('body', '')}" for item in selected))


def ready_batch(plan: dict, states: dict, limit_override: int | None = None) -> list[dict]:
    limit = 1 if plan["team"]["worker_mode"] == "sequential" else min(
        int(limit_override or plan["team"].get("parallel_limit", 1)), int(plan["team"].get("parallel_limit", 1)))
    get_status = lambda value: value.get("status", "pending") if isinstance(value, dict) else (value or "pending")
    active = sum(get_status(value) in {"running", "reviewing"} for value in states.values())
    ready = [task for task in plan["tasks"] if get_status(states.get(task["id"])) == "pending"
             and all(get_status(states.get(dep)) == "done" for dep in task.get("depends_on", []))]
    return ready[:max(0, limit - active)]


def _read(team_id: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
    if not row:
        raise ValueError("team not found")
    result = dict(row)
    result["plan"] = json.loads(result["plan"])
    result["state"] = json.loads(result["state"])
    return result


def _save(team_id: str, *, status=None, plan=None, state=None) -> None:
    with _conn() as c:
        row = c.execute("SELECT status,plan,state FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
        if not row:
            raise ValueError("team not found")
        c.execute("UPDATE glacier_teams SET status=?,plan=?,state=? WHERE team_id=?",
                  (status or row["status"], json.dumps(plan if plan is not None else json.loads(row["plan"])),
                   json.dumps(state if state is not None else json.loads(row["state"])), team_id))


def _save_task(team_id: str, task_id: str, item: dict, status: str | None = None) -> None:
    """Update just one task atomically so parallel task workers cannot overwrite each other's state."""
    with _team_state_lock, _conn() as c:
        row = c.execute("SELECT state,status FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
        if not row:
            raise ValueError("team not found")
        state = json.loads(row["state"])
        state["tasks"][task_id] = item
        _append_progress(state, task_id, item)
        c.execute("UPDATE glacier_teams SET state=?,status=? WHERE team_id=?",
                  (json.dumps(state), status or row["status"], team_id))


def _append_progress(state: dict, task_id: str, item: dict) -> None:
    status = item.get("status")
    if status not in {"done", "retry", "needs_owner", "stopped"}:
        return
    entry = f"Task {task_id}: {status}"
    log = str(state.get("progress_log", ""))
    if entry not in log.splitlines():
        state["progress_log"] = f"{log.rstrip()}\n{entry}".strip()


def _persisted_status(team_id: str) -> str | None:
    try:
        return _read(team_id)["status"]
    except ValueError:
        return None


def _save_feature_evaluation(team_id: str, evaluation: dict) -> None:
    """Persist evaluator evidence without replacing concurrent task updates."""
    with _conn() as c:
        row = c.execute("SELECT state FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
        if not row:
            raise ValueError("team not found")
        state = json.loads(row["state"])
        state.setdefault("features", {})[evaluation["feature_id"]] = {
            "status": "passing", "evaluator_evidence": evaluation["evaluator_evidence"]}
        c.execute("UPDATE glacier_teams SET state=? WHERE team_id=?", (json.dumps(state), team_id))


LEGACY_COMPLETION_NOTE = "legacy: finished before evaluator grading"


def _mark_legacy_completions(plan: dict, state: dict) -> None:
    """Label pre-evaluator completed work while preserving its completed status."""
    tasks = {task["id"]: task for task in plan.get("tasks", [])}
    legacy_ids = []
    for task_id, item in state.get("tasks", {}).items():
        task = tasks.get(task_id, {})
        if (item.get("status") == "done" and task.get("role") not in {"evaluator", "skeptical-evaluator"}
                and not item.get("evaluator_evidence")):
            item["legacy_note"] = LEGACY_COMPLETION_NOTE
            legacy_ids.append(task_id)
    if legacy_ids:
        entries = [f"{LEGACY_COMPLETION_NOTE}: task {task_id}" for task_id in legacy_ids]
        existing = str(state.get("progress_log", ""))
        for entry in entries:
            if entry not in existing:
                existing = f"{existing.rstrip()}\n{entry}".strip()
        state["progress_log"] = existing
    if _uses_feature_evaluators(plan):
        for feature_state in state.get("features", {}).values():
            evidence = feature_state.get("evaluator_evidence")
            if evidence in {"legacy completed task records; final objective check required",
                            "independent governor and final Spec check required"}:
                feature_state.update(status="pending", evaluator_evidence=None)


def _uses_feature_evaluators(plan: dict) -> bool:
    """Feature-linked plans use explicit evaluator tasks; old plans keep their format semantics."""
    return bool(plan.get("features")) and any(task.get("feature_id") for task in plan.get("tasks", []))


def create_vision(vision: dict) -> dict:
    if not isinstance(vision, dict) or not str(vision.get("goal", "")).strip() or not isinstance(vision.get("done"), list) or not vision["done"]:
        raise ValueError("vision needs a goal and a non-empty done list")
    path = f"visions/{uuid.uuid4().hex}.md"
    body = "# Vision\n\n```json\n" + json.dumps(vision, indent=2, ensure_ascii=False) + "\n```\n"
    vault.write_note(path, body, author="owner")
    return {"path": path, "vision": vision}


def read_vision(path: str) -> dict:
    if not re.fullmatch(r"visions/[A-Za-z0-9._-]+\.md", path or ""):
        raise ValueError("Vision path is not allowed")
    text = vault.read_note(path)
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not match:
        raise ValueError("Vision note has no structured Vision")
    return json.loads(match.group(1))


def ask_engine(prompt: str, engine: str, schema: dict | None = None) -> dict:
    """Use the selected Ask adapter for Build responses while keeping its answer shape consistent."""
    if engine not in ASK_ENGINES:
        raise ValueError("Choose one of the available Ask engines.")
    from routes import assistant_chat
    if schema:
        prompt += "\n\nReturn one JSON object matching this schema:\n" + json.dumps(schema)
    answer = assistant_chat._ask_engine(prompt, engine)
    if not isinstance(answer, dict):
        raise ValueError("the selected engine returned an invalid answer")
    return answer


def _structured_plan(answer: dict) -> dict:
    if isinstance(answer.get("reply"), str):
        raw = answer["reply"]
        try:
            value = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except (ValueError, TypeError):
            raise ValueError("the selected engine did not return a structured team plan") from None
        if isinstance(value, dict):
            return value
    return answer


def plan_team(vision: dict, engine: str = "codex") -> dict:
    """Ask the selected existing Ask engine for a structured work plan."""
    if engine not in ASK_ENGINES:
        raise ValueError("Choose one of the available Ask engines.")
    schema = {"type": "object", "additionalProperties": True,
              "required": ["spec", "features", "harness", "team", "tasks", "guards"], "properties": {
                  "spec": {"type": "object"}, "features": {"type": "array"}, "harness": {"type": "object"},
                  "team": {"type": "object"}, "tasks": {"type": "array"}, "guards": {"type": "object"}}}
    prompt = ("Design an evidence-driven build team for this confirmed project. Produce an EARS-style Spec "
              "(requirements, out_of_scope, end-to-end acceptance), a structured feature list, and a harness "
              "(startup_script, smoke_test, checks, progress_log, decision_log). Size the team to project: default "
              "Lead, Builder(s), skeptical Evaluator; add Researcher/Reviewer only when needed. Each feature needs "
              "id,title,description,acceptance. Tasks must reference features. A feature may pass only after evaluator. "
              "The designer is never a team member. Include worker_mode, parallel_limit, and model per role.\nVision:\n" + json.dumps(vision))
    result = _structured_plan(ask_engine(prompt, engine, schema))
    if not isinstance(result, dict):
        raise ValueError("the selected engine did not return a structured team plan")
    result.setdefault("team", {})
    result["team"]["engine"] = engine
    result["team"]["worker_mode"] = "sequential" if engine == "local" else "parallel"
    result["team"]["parallel_limit"] = 1 if engine == "local" else min(5, max(3, int(result["team"].get("parallel_limit", 3))))
    plan = validate_plan({"vision": vision, **result})
    return plan




def save_plan(plan: dict, vision_path: str, workspace: str | None = None) -> dict:
    validate_plan(plan)
    team_id = uuid.uuid4().hex[:16]
    path = f"teams/{team_id}.json"
    vault.write_note(path, json.dumps(plan, indent=2), author="owner")
    state = {"status": "approved", "tasks": {task["id"]: {"status": "pending", "attempts": 0,
             "attempt_limit": 3, "replans": 0} for task in plan["tasks"]},
             "features": {feature["id"]: {"status": "pending", "evaluator_evidence": None} for feature in plan["features"]},
             "events": []}
    with _conn() as c:
        c.execute("INSERT INTO glacier_teams(team_id,status,vision_path,plan,state,workspace) VALUES(?,?,?,?,?,?)",
                  (team_id, "approved", vision_path, json.dumps(plan), json.dumps(state),
                   os.path.abspath(workspace or os.path.join(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), "teams", team_id))))
    return {"team_id": team_id, "status": "approved", "plan_path": path, "plan": plan}


def update_feature(team_id: str, feature_id: str, status: str, evidence: str, actor: str) -> dict:
    """Only the evaluator can mark a feature passing; workers cannot edit the feature catalog."""
    if actor.casefold() not in {"evaluator", "skeptical-evaluator"}:
        raise ValueError("only the evaluator may change feature status")
    if status != "passing" or not str(evidence).strip():
        raise ValueError("evaluator pass with evidence is required")
    row = _read(team_id)
    feature = next((f for f in row["plan"].get("features", []) if f["id"] == feature_id), None)
    if feature is None:
        raise ValueError("feature not found")
    state = row["state"]
    state.setdefault("features", {})[feature_id] = {"status": "passing", "evaluator_evidence": evidence}
    _save(team_id, state=state)
    return state["features"][feature_id]


def build_context(role: dict, feature: dict, contract: dict, progress_log: str, git_history: str = "") -> str:
    """Fresh Builder context is deliberately limited to the approved cycle handoff."""
    if not contract or not contract.get("pass_criteria"):
        raise ValueError("contract must exist before building")
    return (f"Role: {role['id']}\nCharter: {role['charter']}\nSpec excerpt: {feature.get('spec_excerpt', '')}\n"
            f"Feature: {json.dumps(feature, ensure_ascii=False)}\nContract: {json.dumps(contract, ensure_ascii=False)}\n"
            f"Progress log: {progress_log}\nGit history: {git_history}")


def stall_transition(attempts: int, replans: int, evidence: str) -> dict:
    """Bounded stall policy: reset after three attempts; after two smaller re-plans, file claim."""
    if attempts < 3:
        return {"action": "retry", "attempts": attempts, "replans": replans}
    if replans < 2:
        return {"action": "reset_and_replan", "attempts": 0, "replans": replans + 1,
                "handoff_note": evidence}
    return {"action": "claim", "attempts": attempts, "replans": replans, "evidence": evidence}


def _relevant_memory(task: dict) -> list[dict]:
    notes = []
    try:
        paths = memory_context.find(task["title"], k=5)
    except Exception:
        paths = []
    for path in paths:
        try:
            notes.append({"path": path, "body": vault.read_note(path)[:4000]})
        except (OSError, ValueError):
            continue
    return notes


def _worker(context: str, workspace: str, task: dict) -> dict:
    """Run a fresh task through the selected engine; API/model replies are applied as checked patches."""
    engine = task.get("engine", "codex")
    if engine != "codex":
        return _worker_patch(context, workspace, task, engine, task.get("_team_id", ""))
    cfg = {"prompt": context, "sandbox": "workspace-write"}
    timeout = int(task.get("timeout_seconds", 1800))
    try:
        return runner.run_codex("team", "team", task["id"], cfg, "", timeout=timeout, ws=workspace,
                                on_process=lambda process: _register_worker_process(task.get("_team_id", ""), task["id"], process))
    finally:
        _unregister_worker_process(task.get("_team_id", ""), task["id"])


def _worker_patch(context: str, workspace: str, task: dict, engine: str, team_id: str = "") -> dict:
    """Ask non-Codex engines for a unified diff, then validate and apply it in the task workspace."""
    inventory = subprocess.run(["git", "-C", workspace, "ls-files", "--cached", "--others", "--exclude-standard"],
                               capture_output=True, text=True, timeout=10, check=False).stdout.splitlines()
    files = []
    terms = set(re.findall(r"[A-Za-z0-9_.-]{3,}", task.get("title", "").casefold()))
    ranked = sorted(inventory, key=lambda path: (-sum(term in path.casefold() for term in terms), path))
    total = 0
    for relative in ranked[:40]:
        path = os.path.realpath(os.path.join(workspace, relative))
        root = os.path.realpath(workspace)
        if not path.startswith(root + os.sep) or not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                body = handle.read(12000)
        except (OSError, UnicodeError):
            continue
        if total + len(body) > 40000:
            continue
        files.append(f"\n--- {relative} ---\n{body}")
        total += len(body)
    prompt = ("Complete this task and return a JSON object with a string field named reply and a boolean "
              "field named automation. Put only one unified diff in reply and set automation to false. "
              "Do not use tools or run commands. The diff must use paths relative to the workspace, "
              "must not change acceptance checks, and must apply with git apply. Return an empty reply "
              "only if no file change is needed.\n\n" +
              context + "\n\nWorkspace files:\n" + "\n".join(files))
    answer = _run_engine_process(prompt, engine, task, team_id)
    diff = str(answer.get("reply", "")) if isinstance(answer, dict) else str(answer)
    match = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", diff, re.S)
    if match:
        diff = match.group(1).strip()
    if not diff.startswith(("diff --git ", "--- ")):
        return {"output": diff[:12000], "exit_code": 1, "usage": {"route": engine}}
    checked = subprocess.run(["git", "-C", workspace, "apply", "--check", "-"], input=diff,
                             capture_output=True, text=True, timeout=10, check=False)
    if checked.returncode:
        return {"output": f"The {engine} worker returned a patch that does not apply: {checked.stderr[-1000:]}",
                "exit_code": 1, "usage": {"route": engine}}
    applied = subprocess.run(["git", "-C", workspace, "apply", "-"], input=diff,
                             capture_output=True, text=True, timeout=10, check=False)
    return {"output": diff[:12000] if not applied.returncode else applied.stderr[-1000:],
            "exit_code": 0 if not applied.returncode else 1, "usage": {"route": engine}}


def _run_engine_process(prompt: str, engine: str, task: dict, team_id: str) -> dict:
    """Isolate API and subscription calls so Stop can terminate their worker process."""
    if _engine_call_override is not None:
        return _engine_call_override(prompt, engine)
    import sys
    script = ("import json,sys; sys.path.insert(0, " + json.dumps(os.path.dirname(os.path.abspath(__file__))) + "); "
              "from routes import assistant_chat; payload=json.load(sys.stdin); "
              "print(json.dumps(assistant_chat._ask_engine(payload['prompt'], payload['engine'])))")
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen([sys.executable, "-c", script], cwd=os.path.dirname(os.path.abspath(__file__)),
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, **options)
    _register_worker_process(team_id, task["id"], process)
    try:
        stdout, stderr = process.communicate(json.dumps({"prompt": prompt, "engine": engine}),
                                             timeout=int(task.get("timeout_seconds", 1800)))
        if process.returncode:
            raise RuntimeError(f"{engine.title()} worker could not answer: {stderr[-500:]}")
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        runner.terminate_process(process)
        process.communicate()
        raise RuntimeError(f"{engine.title()} worker timed out") from None
    finally:
        _unregister_worker_process(team_id, task["id"])


def _register_worker_process(team_id: str, task_id: str, process) -> None:
    if not team_id:
        return
    with _worker_process_lock:
        if _persisted_status(team_id) == "stopped":
            runner.terminate_process(process)
            return
        _worker_processes[(team_id, task_id)] = process


def _unregister_worker_process(team_id: str, task_id: str) -> None:
    with _worker_process_lock:
        _worker_processes.pop((team_id, task_id), None)


def _terminate_worker_processes(team_id: str) -> None:
    with _worker_process_lock:
        processes = [(key, process) for key, process in _worker_processes.items() if key[0] == team_id]
    for key, process in processes:
        if process.poll() is None:
            runner.terminate_process(process)
        _unregister_worker_process(*key)


def _review(plan: dict, task: dict, output: str, attempt: int) -> dict:
    role_id = plan["team"].get("supervisor") or plan["tasks"][0]["role"]
    _forbid_planner(role_id, "supervisor")
    role = next((item for item in plan["team"]["roles"] if item["id"] == role_id), None)
    if not role:
        return {"passed": False, "evidence": "the plan has no valid supervisor role"}
    import decider
    criteria = "Review the handover against the supervisor charter and task acceptance checks. Reject incomplete, unsupported, or off-plan work."
    decision = decider.decide(criteria + "\nSupervisor charter: " + role["charter"] + "\nTask: " + task["title"],
                              ["pass", "fail"], output or "(empty handover)")
    return {"passed": decision.get("choice") == "pass", "evidence": f"supervisor review ({decision.get('engine')}): {decision.get('choice')}"}


def _check_task(task: dict, output: str, workspace: str) -> dict:
    evidence = []
    for check in task["acceptance"]:
        result = verify.run_check(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), "team", check, output, workspace)
        evidence.append(result)
        if not result["passed"] and check.get("required", True):
            return {"passed": False, "evidence": evidence}
    return {"passed": True, "evidence": evidence}


def _govern(plan: dict, results: dict) -> dict:
    done = {task_id for task_id, item in results.items() if item.get("status") == "done"}
    expected = {task["id"] for task in plan["tasks"]}
    if done != expected:
        return {"passed": False, "evidence": "some planned tasks are incomplete"}
    import decider
    outputs = {task_id: item.get("output", "") for task_id, item in results.items()}
    decision = decider.decide("Compare the completed results with every item in the Vision done list and the approved plan. "
                              "Pass only when the work clearly meets them. Vision done list: " +
                              json.dumps(plan["vision"].get("done", [])) + "\nPlan results: " + json.dumps(outputs),
                              ["pass", "fail"])
    passed = decision.get("choice") == "pass"
    return {"passed": passed, "evidence": f"final governor ({decision.get('engine')}): {decision.get('choice')}"}


def _objective_check(plan: dict, workspace: str) -> dict:
    """Run the approved Spec's end-to-end checks before any team can become done."""
    acceptance = (plan.get("spec") or {}).get("acceptance", [])
    if not acceptance:
        return {"passed": False, "evidence": "Spec has no end-to-end acceptance checks"}
    if all(isinstance(item, dict) for item in acceptance):
        verify.validate(acceptance)
        checks = acceptance
        results = [verify.run_check(os.path.abspath(os.environ.get("GLACIER_HOME", "data")),
                                    "team-objective", check, "", workspace) for check in checks]
        return {"passed": all(item.get("passed") for item in results), "evidence": results}
    # Plain EARS acceptance statements are graded independently by the evaluator engine.
    import decider
    decision = decider.decide("Check the final project against this approved end-to-end Spec acceptance. "
                              "Pass only with clear evidence from the completed project.\nAcceptance: " +
                              json.dumps(acceptance, ensure_ascii=False), ["pass", "fail"],
                              "Workspace: " + os.path.abspath(workspace))
    return {"passed": decision.get("choice") == "pass",
            "evidence": f"spec objective check ({decision.get('engine')}): {decision.get('choice')}"}


def execute_task(team_id: str, task_id: str, plan: dict, task: dict, workspace: str, state: dict, attempt: int = 1) -> dict:
    role = next(role for role in plan["team"]["roles"] if role["id"] == task["role"])
    _forbid_planner(role["id"], "task role")
    effective_task = dict(task)
    team_config = plan.get("team", {})
    effective_task["engine"] = team_config.get("engine") or ("local" if team_config.get("worker_mode") == "sequential" else "codex")
    effective_task["_team_id"] = team_id
    effective_task["timeout_seconds"] = int(task.get("timeout_seconds") or (plan.get("guards") or {}).get("task_timeout_seconds", 1800))
    feature_id = task.get("feature_id")
    feature = next((item for item in plan.get("features", []) if item.get("id") == feature_id), None)
    contract = task.get("contract")
    if feature and task.get("role") not in ("lead", "evaluator", "skeptical-evaluator") and (not contract or not contract.get("pass_criteria")):
        return {"status": "retry", "output": "", "review": {"passed": False, "evidence": "contract missing"},
                "checks": {"passed": False, "evidence": "contract must exist before building"}}
    if feature and task.get("role") == "builder":
        context = build_context(role, feature, contract, str(state.get("progress_log", "")),
                                str(state.get("git_history", "")))
    else:
        context = task_context(role, effective_task, _relevant_memory(task), plan.get("vision"))
    os.makedirs(workspace, exist_ok=True)
    try:
        result = _worker(context, workspace, effective_task)
    except Exception:
        if _persisted_status(team_id) == "stopped":
            return {"status": "stopped", "output": "Worker stopped by the owner."}
        return {"status": "retry", "output": "The selected engine could not complete this task.",
                "review": {"passed": False, "evidence": "worker did not return a result"},
                "checks": {"passed": False, "evidence": "worker did not return a result"}}
    output = str(result.get("output", ""))
    store.broadcaster.publish({"type": "team_handover", "team_id": team_id, "task_id": task_id, "role": role["id"]})
    review = _review(plan, task, output, attempt)
    store.broadcaster.publish({"type": "team_review_result", "team_id": team_id, "task_id": task_id,
                               "passed": bool(review.get("passed")), "evidence": review.get("evidence", "")})
    checks = _check_task(task, output, workspace) if review.get("passed") else {"passed": False, "evidence": review.get("evidence")}
    if not review.get("passed") or not checks.get("passed") or result.get("exit_code", 1) != 0:
        return {"status": "retry", "output": output, "review": review, "checks": checks}
    if feature and task.get("role") in ("evaluator", "skeptical-evaluator"):
        feature_state = state.setdefault("features", {}).get(feature_id, {})
        feature_state.update(status="passing", evaluator_evidence=json.dumps(checks.get("evidence", [])))
    return {"status": "awaiting_approval" if task.get("requires_approval") else "done",
            "output": output, "review": review, "checks": checks,
            **({"feature_evaluation": {"feature_id": feature_id,
                 "evaluator_evidence": json.dumps(checks.get("evidence", []))}}
               if feature and task.get("role") in ("evaluator", "skeptical-evaluator") else {})}


def stuck_claim(run_id: str, task_id: str, attempts: int, evidence: str) -> str:
    return claims.file_claim("bug", f"Team task {task_id} is stuck", evidence, run_id=run_id, node_id=task_id,
                             attempts_made=attempts, filed_by="glacier-team-runner")["id"]


def run_team_local(team_id: str, plan: dict, workspace: str, state: dict | None = None) -> dict:
    """Synchronous testable engine. Production workflow uses durable per-task workflow steps below."""
    state = state or {"status": "running", "tasks": {t["id"]: {"status": "pending", "attempts": 0} for t in plan["tasks"]}}
    def persist_task(task_id: str, item: dict) -> None:
        if _persisted_status(team_id) is not None:
            _save_task(team_id, task_id, item)
    _mark_legacy_completions(plan, state)
    state.setdefault("features", {feature["id"]: {"status": "pending", "evaluator_evidence": None}
                                   for feature in plan.get("features", [])})
    if plan.get("features") and not _uses_feature_evaluators(plan):
        # Older persisted runs have no feature records. Rebuild evaluator evidence from
        # their independently reviewed, completed task results when resuming.
        for feature in plan["features"]:
            related = [task for task in plan.get("tasks", []) if task.get("feature_id") in (None, feature["id"])]
            # Legacy fixture/runtime records saved only `done`; when no structured
            # evidence exists, require all downstream work plus the final objective check.
            if related and all(state.get("tasks", {}).get(task["id"], {}).get("status") == "done"
                               for task in related):
                state["features"][feature["id"]] = {"status": "passing",
                    "evaluator_evidence": "legacy completed task records; final objective check required"}
    limit = int((plan.get("guards") or {}).get("max_retries", 2))
    while True:
        batch = ready_batch(plan, state["tasks"])
        if not batch:
            break
        def run_one(task):
            task_id = task["id"]
            item = state["tasks"].setdefault(task_id, {"status": "pending", "attempts": 0})
            item["status"] = "running"
            item["attempts"] += 1
            persist_task(task_id, item)
            store.broadcaster.publish({"type": "team_task_taken", "team_id": team_id, "task_id": task_id, "role": task["role"]})
            task_workspace = workspace
            if plan["team"]["worker_mode"] == "parallel":
                task_workspace = os.path.join(workspace, "worktrees", task_id)
                os.makedirs(task_workspace, exist_ok=True)
            result = execute_task(team_id, task_id, plan, task, task_workspace, state, item["attempts"])
            return task, item, result
        if plan["team"]["worker_mode"] == "parallel" and len(batch) > 1:
            with ThreadPoolExecutor(max_workers=int(plan["team"].get("parallel_limit", 1))) as pool:
                outcomes = list(pool.map(run_one, batch))
        else:
            outcomes = [run_one(task) for task in batch]
        for task, item, result in outcomes:
            task_id = task["id"]
            if result["status"] == "awaiting_approval":
                item.update(result)
                persist_task(task_id, item)
                continue
            if result["status"] == "done":
                item.update(result)
                item["status"] = "done"
                persist_task(task_id, item)
                continue
            if item["attempts"] >= limit:
                cid = stuck_claim(team_id, task_id, item["attempts"], json.dumps(result))
                item.update(status="needs_owner", claim_id=cid, **result)
                persist_task(task_id, item)
                state["status"] = "needs_owner"
                store.broadcaster.publish({"type": "team_needs_owner", "team_id": team_id, "task_id": task_id, "claim_id": cid})
                return state
            item.update(status="pending", **result)
            persist_task(task_id, item)
        persisted_status = _persisted_status(team_id)
        if persisted_status in {"pausing", "paused", "stopped"}:
            current = _read(team_id)
            final_status = "paused" if persisted_status == "pausing" else persisted_status
            current["state"]["status"] = final_status
            _save(team_id, status=final_status, state=current["state"])
            return {**current["state"], "status": final_status}
        if plan.get("features") and not _uses_feature_evaluators(plan):
            for feature in plan["features"]:
                related = [task for task in plan.get("tasks", []) if task.get("feature_id") in (None, feature["id"])]
                completed = [state.get("tasks", {}).get(task["id"], {}) for task in related]
                if completed and all(item.get("status") == "done" for item in completed):
                    state["features"][feature["id"]] = {"status": "passing",
                        "evaluator_evidence": "legacy completed task records; final objective check required"}
        # The production worker loop is serial for sequential/local mode; parallel mode is scheduled below.
    if any(item.get("status") == "awaiting_approval" for item in state["tasks"].values()):
        state["status"] = "waiting"
        return state
    if any(item.get("status") != "done" for item in state["tasks"].values()):
        state["status"] = "waiting"
        return state
    governed = _govern(plan, state["tasks"])
    if governed.get("passed") and plan.get("features") and not _uses_feature_evaluators(plan):
        for feature in plan["features"]:
            state["features"][feature["id"]] = {"status": "passing",
                "evaluator_evidence": "independent governor and final Spec check required"}
    feature_states = state.get("features", {})
    features_passed = all(feature_states.get(feature["id"], {}).get("status") == "passing"
                          for feature in plan.get("features", []))
    objective = _objective_check(plan, workspace) if governed["passed"] and features_passed else {
        "passed": False, "evidence": "features are not all evaluator-approved"}
    state["governor"] = governed
    state["objective_check"] = objective
    state["status"] = "done" if governed["passed"] and features_passed and objective["passed"] else "needs_owner"
    store.broadcaster.publish({"type": "team_done" if state["status"] == "done" else "team_needs_owner", "team_id": team_id})
    return state


@DBOS.step(retries_allowed=True, max_attempts=3)
def team_task_step(team_id: str, task_id: str) -> dict:
    row = _read(team_id)
    plan, state = row["plan"], row["state"]
    task = next(t for t in plan["tasks"] if t["id"] == task_id)
    current = state["tasks"][task_id]
    current["attempts"] = int(current.get("attempts", 0)) + 1
    current["status"] = "running"
    _save_task(team_id, task_id, current)
    store.broadcaster.publish({"type": "team_task_taken", "team_id": team_id, "task_id": task_id, "role": task["role"]})
    task_workspace = row["workspace"]
    if plan["team"]["worker_mode"] == "parallel":
        task_workspace = runner.workspaces.prepare(os.path.abspath(os.environ.get("GLACIER_HOME", "data")),
                                                   f"team-{team_id}", f"{team_id}-{task_id}", True)
    result = execute_task(team_id, task_id, plan, task, task_workspace, state, current["attempts"])
    current.update(result)
    evaluation = result.get("feature_evaluation")
    if plan["team"]["worker_mode"] == "parallel" and result.get("status") == "done":
        runner.workspaces.finish(os.path.abspath(os.environ.get("GLACIER_HOME", "data")),
                                 f"team-{team_id}", f"{team_id}-{task_id}", True)
    _save_task(team_id, task_id, current)
    if evaluation:
        _save_feature_evaluation(team_id, evaluation)
    return result


@DBOS.workflow()
def team_task_workflow(team_id: str, task_id: str) -> dict:
    return team_task_step(team_id, task_id)


@DBOS.workflow()
def run_team(team_id: str) -> str:
    row = _read(team_id)
    plan, state = row["plan"], row["state"]
    _mark_legacy_completions(plan, state)
    state["status"] = "running"
    _save(team_id, status="running", state=state)
    store.broadcaster.publish({"type": "team_started", "team_id": team_id})
    max_retries = int((plan.get("guards") or {}).get("max_retries", 2))
    while True:
        row = _read(team_id)
        plan, state = row["plan"], row["state"]
        batch = ready_batch(plan, state["tasks"])
        if not batch:
            waiting = [task_id for task_id, item in state["tasks"].items() if item.get("status") == "awaiting_approval"]
            if not waiting:
                break
            state["status"] = "waiting"
            _save(team_id, status="waiting", state=state)
            store.broadcaster.publish({"type": "team_needs_owner", "team_id": team_id, "tasks": waiting})
            message = DBOS.recv(topic="owner_approval", timeout_seconds=7 * 24 * 3600)
            if not message:
                return "waiting"
            item = state["tasks"].get(message.get("task_id"))
            if item and item.get("status") == "awaiting_approval":
                item["status"] = "pending" if message.get("approved") else "rejected"
                if not message.get("approved"):
                    state["status"] = "needs_owner"
                    _save(team_id, status="needs_owner", state=state)
                    return "needs_owner"
                state["status"] = "running"
                _save(team_id, status="running", state=state)
            continue
        futures = []
        for task in batch:
            tid = task["id"]
            current = state["tasks"][tid]
            current["status"] = "running"
            _save(team_id, state=state)
            child_id = f"{team_id}-{tid}-{int(current.get('attempts', 0)) + 1}"
            with SetWorkflowID(child_id):
                futures.append(DBOS.start_workflow(team_task_workflow, team_id, tid))
        for future in futures:
            future.get_result()
        row = _read(team_id)
        state = row["state"]
        for task in plan["tasks"]:
            item = state["tasks"][task["id"]]
            if item.get("status") == "retry":
                if int(item.get("attempts", 0)) >= max_retries:
                    cid = stuck_claim(team_id, task["id"], item["attempts"], json.dumps(item))
                    item.update(status="needs_owner", claim_id=cid)
                    state["status"] = "needs_owner"
                    _save(team_id, status="needs_owner", state=state)
                    store.broadcaster.publish({"type": "team_needs_owner", "team_id": team_id, "task_id": task["id"], "claim_id": cid})
                    return "needs_owner"
                item["status"] = "pending"
        _save(team_id, state=state)
    row = _read(team_id)
    state = row["state"]
    governed = _govern(row["plan"], state["tasks"])
    feature_states = state.get("features", {})
    features_passed = all(feature_states.get(feature["id"], {}).get("status") == "passing"
                          for feature in row["plan"].get("features", []))
    objective = _objective_check(row["plan"], row["workspace"]) if governed["passed"] and features_passed else {
        "passed": False, "evidence": "features are not all evaluator-approved"}
    state["governor"] = governed
    state["objective_check"] = objective
    state["status"] = "done" if governed["passed"] and features_passed and objective["passed"] else "needs_owner"
    _save(team_id, status=state["status"], state=state)
    store.broadcaster.publish({"type": "team_done" if governed["passed"] else "team_needs_owner", "team_id": team_id})
    return state["status"]


def start(team_id: str) -> str:
    row = _read(team_id)
    if row["status"] not in ("approved", "waiting", "running"):
        raise ValueError("team plan must be approved before it can run")
    with _conn() as c:
        c.execute("UPDATE glacier_teams SET status='running' WHERE team_id=?", (team_id,))
    with SetWorkflowID(team_id):
        DBOS.start_workflow(run_team, team_id)
    return team_id


def approval(team_id: str, task_id: str, approved: bool) -> dict:
    row = _read(team_id)
    task = row["state"]["tasks"].get(task_id)
    if not task or task.get("status") != "awaiting_approval":
        raise ValueError("task is not waiting for approval")
    DBOS.send(team_id, {"task_id": task_id, "approved": bool(approved)}, topic="owner_approval")
    return {"team_id": team_id, "task_id": task_id, "approved": approved}


def summary() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT team_id,status,plan,state FROM glacier_teams WHERE status IN ('running','waiting','needs_owner') ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        state = json.loads(row["state"])
        plan = json.loads(row["plan"])
        feature_states = state.get("features", {})
        result.append({"team_id": row["team_id"], "name": str(plan.get("vision", {}).get("goal", row["team_id"])), "status": row["status"], "done": sum(x.get("status") == "done" for x in state["tasks"].values()),
                       "tasks": len(state["tasks"]), "passing": sum(feature_states.get(f["id"], {}).get("status") == "passing" for f in plan.get("features", [])),
                       "feature_count": len(plan.get("features", [])), "needs_owner": sum(x.get("status") in {"needs_owner", "awaiting_approval"} for x in state["tasks"].values())})
    return result


def get(team_id: str) -> dict:
    row = _read(team_id)
    return {"team_id": team_id, "status": row["status"], "vision_path": row["vision_path"], "plan": row["plan"], **row["state"]}


def control(team_id: str, action: str) -> dict:
    if action not in {"pause", "resume", "stop"}:
        raise ValueError("unknown team action")
    with _team_state_lock:
        row = _read(team_id)
        status = row["status"]
        allowed = {"pause": {"running"}, "resume": {"paused"},
                   "stop": {"running", "pausing", "paused", "waiting", "approved"}}
        if status not in allowed[action]: raise ValueError(f"team cannot {action} while {status}")
        active = any(item.get("status") in {"running", "reviewing"} for item in row["state"].get("tasks", {}).values())
        next_status = {"pause": "pausing" if active else "paused", "resume": "running", "stop": "stopped"}[action]
        row["state"]["status"] = next_status
        if action == "resume":
            workflow_id = f"{team_id}-resume-{uuid.uuid4().hex[:10]}"
            row["state"]["workflow_id"] = workflow_id
        if action == "stop":
            for task_id, item in row["state"].get("tasks", {}).items():
                if item.get("status") in {"running", "reviewing"}:
                    item["status"] = "stopped"
                    _append_progress(row["state"], task_id, item)
        _save(team_id, status=next_status, state=row["state"])
    event_name = {"pause": "team.paused", "resume": "team.resumed", "stop": "team.stopped"}[action]
    audit_log.record(event_name, what={"team_id": team_id, "status": next_status})
    if action == "stop":
        _terminate_worker_processes(team_id)
        if status == "waiting":
            DBOS.send(row["state"].get("workflow_id", team_id), {"action": "stop"}, topic="owner_approval")
    elif action == "resume":
        with SetWorkflowID(row["state"]["workflow_id"]):
            DBOS.start_workflow(run_team, team_id)
    return {"team_id": team_id, "status": next_status}

def remove(team_id: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM glacier_teams WHERE team_id=?", (team_id,)).fetchone()
        if not row: raise ValueError("team not found")
        saved = dict(row)
        if saved["status"] in {"running", "paused"}: raise ValueError("stop the team before deleting it")
        c.execute("DELETE FROM glacier_teams WHERE team_id=?", (team_id,))
    return saved

def restore(saved: dict) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO glacier_teams(team_id,status,vision_path,plan,state,workspace,created_at) VALUES(?,?,?,?,?,?,?)",
                  tuple(saved.get(key) for key in ("team_id", "status", "vision_path", "plan", "state", "workspace", "created_at")))

init()
