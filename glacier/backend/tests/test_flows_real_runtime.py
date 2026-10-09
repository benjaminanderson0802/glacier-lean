"""Real-backend workflow proofs; optional external engines skip with an explanation."""

from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import shutil
import shlex
import socketserver
import subprocess
import sys
import threading
import time

import pytest

from conftest import BACKEND, Server, env


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "templates" / "manifest" / "MANIFEST.json"


class RealCodexServer(Server):
    """Backend process that uses the installed official Codex CLI, never the fake."""

    def start(self):
        import sys
        from conftest import free_port

        self.port = free_port()
        binary = shutil.which("codex") or "codex"
        child_env = dict(os.environ, GLACIER_HOME=self.home, CODEX_BIN=binary)
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(self.port)],
                                     cwd=BACKEND, env=child_env, stdout=self.log, stderr=subprocess.STDOUT, **options)
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                break
            try:
                import httpx
                if httpx.get(self.url + "/api/environments").status_code == 200:
                    return self
            except Exception:
                pass
            time.sleep(0.1)
        message = self.diagnostics()
        self.stop()
        raise RuntimeError(f"real backend did not start:\n{message}")


def _ollama_available(model="granite3.3:2b"):
    import urllib.request

    base = os.environ.get("GLACIER_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    # conftest deliberately points ordinary tests at port 9. This module is an
    # exception: when it sees that sentinel, probe Ollama's normal local endpoint.
    candidates = ["http://127.0.0.1:11434"] if base == "http://127.0.0.1:9" else [base]
    for candidate in candidates:
        try:
            with urllib.request.urlopen(candidate + "/api/tags", timeout=2) as response:
                models = json.load(response).get("models", [])
            if any(item.get("name") == model or item.get("model") == model for item in models):
                return True, candidate
        except Exception:
            pass
    return False, candidates[0]


def _require_ollama(model="granite3.3:2b"):
    available, base = _ollama_available(model)
    if not available:
        pytest.skip(f"Ollama model {model} unavailable at {base}; install/start Ollama and pull the model to run this real-engine flow")
    return base


def _require_codex():
    binary = shutil.which("codex")
    if not binary:
        pytest.skip("Codex subscription CLI is not installed; install the official CLI and sign in to run this flow")
    result = subprocess.run([binary, "login", "status"], capture_output=True, text=True, timeout=10)
    if result.returncode:
        pytest.skip("Codex subscription CLI is installed but not signed in; run codex login --device-auth to run this flow")
    return binary


def test_real_schedule_command_check_note_history_undo_and_explanation(server):
    graph = env("real-schedule-proof", [
        ("schedule", "schedule", {"cron": "*/2 * * * * *"}),
        ("command", "command", {"cmd": "printf 'glacier-proof-marker\\n'"}),
        ("check", "check", {"expr": "exit_code == 0"}),
        ("note", "note", {"path": "runs/{env}-{run}.md", "template": "Verified marker {prev_output}"}),
    ], [("schedule", "command", ""), ("command", "check", ""), ("check", "note", "yes")])
    server.put("/api/environments/real-schedule-proof", graph)

    deadline = time.time() + 20
    scheduled = []
    while time.time() < deadline:
        scheduled = [row for row in server.get("/api/runs", params={"env_id": "real-schedule-proof"}) if row["status"] == "done"]
        if scheduled:
            break
        time.sleep(0.25)
    assert scheduled, "the real scheduler did not start the flow"
    run_id = scheduled[0]["run_id"]
    run = server.get(f"/api/runs/{run_id}")
    assert run["node_states"] == {"schedule": "done", "command": "done", "check": "done", "note": "done"}
    assert "glacier-proof-marker" in run["outputs"]["command"]
    path = f"runs/real-schedule-proof-{run_id}.md"
    assert "glacier-proof-marker" in server.get("/api/vault/note", params={"path": path})["body"]
    assert any(item["run_id"] == run_id for item in server.get("/api/runs", params={"env_id": "real-schedule-proof"}))
    explained = server.get(f"/api/runs/{run_id}/explain")
    assert "finished" in explained["summary"].lower() and any(step["label"] == "Command" for step in explained["steps"])
    history = server.get("/api/memory/history", params={"path": path})
    assert history and history[0]["commit"]
    server.put("/api/memory/note", {"path": path, "body": "temporary replacement", "author": "owner"})
    replacement = server.get("/api/memory/history", params={"path": path})[0]["commit"]
    server.post("/api/memory/undo", {"path": path, "commit": replacement})
    assert "glacier-proof-marker" in server.get("/api/vault/note", params={"path": path})["body"]


def test_real_local_ai_waits_for_approval_then_runs_command(make_server, tmp_path, monkeypatch):
    base = _require_ollama()
    monkeypatch.setenv("GLACIER_OLLAMA_URL", base)
    home = tmp_path / "approval-home"
    home.mkdir()
    server = make_server()
    server.home = str(home)
    server.start()
    graph = env("real-local-approval", [
        ("manual", "command", {"cmd": "printf 'Please summarize the word glacier.'"}),
        ("ai", "local_ai", {"model": "granite3.3:2b", "prompt": "In one short sentence summarize: {prev_output}", "timeout": "120"}),
        ("approval", "approval", {"prompt": "Approve this locally generated result?"}),
        ("command", "command", {"cmd": "printf 'approved command ran'"}),
    ], [("manual", "ai", ""), ("ai", "approval", ""), ("approval", "command", "yes")])
    server.put("/api/environments/real-local-approval", graph)
    run_id = server.post("/api/environments/real-local-approval/run")["run_id"]
    waiting = server.wait_run(run_id, ("waiting",), timeout=180)
    assert waiting["node_states"]["ai"] == "done" and waiting["waiting_on"] == "approval"
    assert waiting["usage"]["ai"]["route"] == "local/ollama"
    server.kill()
    server.start()
    waiting = server.get(f"/api/runs/{run_id}")
    assert waiting["status"] == "waiting" and waiting["waiting_on"] == "approval"
    assert server.post(f"/api/runs/{run_id}/approve", {"node_id": "approval", "approved": True}) == {"ok": True}
    complete = server.wait_run(run_id, timeout=30)
    assert complete["status"] == "done" and complete["node_states"]["command"] == "done"
    assert "approved command ran" in complete["outputs"]["command"]


def test_real_http_decide_routes_to_one_of_two_notes(make_server, tmp_path, monkeypatch):
    base = _require_ollama()
    monkeypatch.setenv("GLACIER_OLLAMA_URL", base)
    home = tmp_path / "http-home"
    home.mkdir()
    server = make_server()
    server.home = str(home)
    server.start()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            payload = b'{"category":"alpha","text":"route alpha"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as local:
        thread = threading.Thread(target=local.serve_forever, daemon=True)
        thread.start()
        try:
            graph = env("real-http-decide", [
                ("manual", "command", {"cmd": "printf 'classify this response'"}),
                ("http", "http_request", {"url": f"http://127.0.0.1:{local.server_address[1]}/event",
                    "method": "GET", "allowed_sites": "127.0.0.1", "allow_private_network": "Yes", "body_type": "JSON"}),
                ("decide", "decide", {"question": "Which branch matches category alpha? {prev_output}",
                    "options": "alpha, beta", "engine": "local", "model": "granite3.3:2b"}),
                ("alpha", "note", {"path": "notes/alpha-{run}.md", "template": "alpha branch {prev_output}"}),
                ("beta", "note", {"path": "notes/beta-{run}.md", "template": "beta branch"}),
            ], [("manual", "http", ""), ("http", "decide", ""), ("decide", "alpha", "alpha"), ("decide", "beta", "beta")])
            server.put("/api/environments/real-http-decide", graph)
            run_id = server.post("/api/environments/real-http-decide/run")["run_id"]
            run = server.wait_run(run_id, timeout=180)
            assert run["status"] == "done", run
            assert run["node_states"]["http"] == "done" and '"category": "alpha"' in run["outputs"]["http"]
            assert run["node_states"]["alpha"] == "done" and run["node_states"]["beta"] == "skipped"
            assert "alpha" in server.get("/api/vault/note", params={"path": f"notes/alpha-{run_id}.md"})["body"]
        finally:
            local.shutdown()
            thread.join(timeout=2)


def test_real_loop_and_subflow_have_nested_history(server, tmp_path):
    counter = tmp_path / "loop-count.txt"
    child = env("real-loop-child", [("c", "command", {"cmd": "printf child-ran"}),
        ("n", "note", {"path": "notes/child-{run}.md", "template": "{prev_output}"})], [("c", "n", "")])
    server.put("/api/environments/real-loop-child", child)
    parent = env("real-loop-parent", [
        ("start", "command", {"cmd": "true"}), ("loop", "loop", {"times": "2"}),
        ("tick", "command", {"cmd": f"printf 'tick\\n' >> '{counter}'"}),
        ("sub", "flow", {"env": "real-loop-child"}),
        ("note", "note", {"path": "notes/parent-{run}.md", "template": "{summary}"}),
    ], [("start", "loop", ""), ("loop", "tick", "again"), ("tick", "loop", ""),
        ("loop", "sub", "done"), ("sub", "note", "")])
    server.put("/api/environments/real-loop-parent", parent)
    run_id = server.post("/api/environments/real-loop-parent/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "done" and counter.read_text().splitlines() == ["tick", "tick"]
    assert "2 of 2" in run["outputs"]["loop"]
    child_runs = server.get("/api/runs", params={"env_id": "real-loop-child"})
    assert len(child_runs) == 1 and child_runs[0]["status"] == "done"


def test_real_backend_resumes_after_forced_restart(make_server, tmp_path):
    home = tmp_path / "restart-home"
    home.mkdir()
    server = make_server()
    server.home = str(home)
    server.start()
    marks = home / "marks"
    helper = home / "mark_step.py"
    helper.write_text(
        "import pathlib, sys, time\n"
        "name, mark, started = sys.argv[1:]\n"
        "if started != '-': pathlib.Path(started).touch()\n"
        "if name == 'slow': time.sleep(10)\n"
        "with pathlib.Path(mark).open('a') as output: output.write(name + '\\n')\n",
        encoding="utf-8",
    )
    def invoke(name, started="-"):
        return shlex.join([sys.executable, str(helper), name, str(marks), started])
    graph = env("real-survive", [
        ("first", "command", {"cmd": invoke("first")}),
        ("slow", "command", {"cmd": invoke("slow", str(home / "slow-started"))}),
        ("last", "command", {"cmd": invoke("last")}),
    ], [("first", "slow", ""), ("slow", "last", "")])
    server.put("/api/environments/real-survive", graph)
    run_id = server.post("/api/environments/real-survive/run")["run_id"]
    deadline = time.time() + 15
    while time.time() < deadline:
        state = server.get(f"/api/runs/{run_id}")
        if state["node_states"].get("slow") == "running" and (home / "slow-started").exists():
            break
        time.sleep(0.1)
    assert state["node_states"]["slow"] == "running" and (home / "slow-started").exists()
    assert marks.read_text().splitlines() == ["first"]
    server.kill()
    server.start()
    run = server.wait_run(run_id, timeout=45)
    assert run["status"] == "done"
    assert marks.read_text().splitlines().count("first") == 1
    assert marks.read_text().splitlines().count("last") == 1
    # The interrupted command is retried on recovery; the detached first attempt may also finish.
    assert marks.read_text().splitlines().count("slow") in (1, 2)
    assert [item["run_id"] for item in server.get("/api/runs", params={"env_id": "real-survive"})] == [run_id]


def test_real_codex_worker_creates_checked_file_in_temporary_folder(make_server, tmp_path):
    binary = _require_codex()
    home = tmp_path / "codex-home"
    workspace = tmp_path / "tiny-codex-task"
    home.mkdir()
    workspace.mkdir()
    verify_script = workspace / "verify_hello.py"
    verify_script.write_text(
        "import pathlib, sys\n"
        "assert pathlib.Path(sys.argv[1]).read_text().strip() == 'hello'\n",
        encoding="utf-8",
    )
    server = RealCodexServer(home)
    try:
        server.start()
        graph = env("real-codex-proof", [
            ("worker", "codex", {"prompt": "Create hello.txt containing exactly hello and make no other changes.",
                "workdir": str(workspace), "sandbox": "workspace-write", "timeout": "180"}),
            ("check", "command", {"cmd": shlex.join([sys.executable, str(verify_script), str(workspace / "hello.txt")])}),
        ], [("worker", "check", "")])
        server.put("/api/environments/real-codex-proof", graph)
        run_id = server.post("/api/environments/real-codex-proof/run")["run_id"]
        run = server.wait_run(run_id, timeout=240)
        assert run["status"] == "done" and run["node_states"]["check"] == "done", run
        assert (workspace / "hello.txt").read_text().strip() == "hello"
    finally:
        server.stop()


@pytest.fixture(scope="module")
def real_template_backend(tmp_path_factory):
    root = tmp_path_factory.mktemp("real-template-backend")
    home = root / "home"
    home.mkdir()
    # The web-page template uses a local fixture below. This opt-in resolver only
    # changes the isolated test backend process, never the user's running backend.
    shim = root / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(
        "import egress\n"
        "egress._resolve_public = lambda host: ['127.0.0.1']\n",
        encoding="utf-8",
    )
    old_pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(filter(None, [str(shim), str(BACKEND), old_pythonpath]))
    server = RealCodexServer(home)
    saved_ollama = os.environ.get("GLACIER_OLLAMA_URL")
    _available, local_url = _ollama_available()
    os.environ["GLACIER_OLLAMA_URL"] = local_url
    server.start()
    if saved_ollama is not None:
        os.environ["GLACIER_OLLAMA_URL"] = saved_ollama
    else:
        os.environ.pop("GLACIER_OLLAMA_URL", None)
    try:
        yield server, root
    finally:
        server.stop()
        if old_pythonpath:
            os.environ["PYTHONPATH"] = old_pythonpath
        else:
            os.environ.pop("PYTHONPATH", None)


@pytest.mark.parametrize(
    "template_id",
    [entry["id"] for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["templates"]],
)
def test_each_installable_template_installs_and_runs_or_skips_for_missing_engine(real_template_backend, template_id):
    server, root = real_template_backend
    templates = {item["id"]: item for item in server.get("/api/templates")}
    item = templates[template_id]
    assert item["installable"] is True, f"{template_id} is unavailable: {item['review_status']}"
    flow = json.loads(json.dumps(item["template"]))
    env_id = "proof-" + template_id.removeprefix("tpl-")
    flow["id"], flow["name"] = env_id, "Template proof " + template_id
    flow.pop("description", None)
    flow.pop("when_to_use", None)
    nodes = {node["id"]: node for node in flow["nodes"]}
    home = Path(server.home)
    workspace = home / "workspaces" / env_id
    workspace.mkdir(parents=True, exist_ok=True)

    codex_needed = any(node["type"] == "codex" for node in nodes.values())
    if codex_needed:
        _require_codex()
    local_needed = any(node["type"] == "local_ai" for node in nodes.values())
    if local_needed:
        _require_ollama()

    for node in nodes.values():
        cfg = node.get("config", {})
        if node["type"] == "schedule":
            cfg["cron"] = "0 0 1 1 *"  # template remains installable, but the proof invokes it manually
        elif node["type"] == "read_document":
            source = workspace / "fixture.txt"
            source.write_text("Meeting: send the agenda to the team. Launch is Friday.", encoding="utf-8")
            cfg["source"] = str(source)
        elif node["type"] == "command":
            cmd = cfg.get("cmd", "")
            cmd = cmd.replace('"$HOME/Downloads"', f'"{home / "Downloads"}"')
            cmd = cmd.replace('"$HOME/Backups"', f'"{home / "Backups"}"')
            cfg["cmd"] = cmd
        elif node["type"] == "codex":
            cfg["workdir"] = str(workspace)
        elif node["type"] == "local_ai":
            cfg["model"] = "granite3.3:2b"
        elif node["type"] == "decide":
            cfg["engine"] = "codex" if not local_needed else "local"
            cfg["model"] = "granite3.3:2b"
        elif node["type"] == "flow" and cfg.get("env") == "tpl-daily-report":
            child = next(json.loads((ROOT / "templates" / entry["file"]).read_text(encoding="utf-8"))
                         for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["templates"]
                         if entry["id"] == "tpl-daily-report")
            child_id = env_id + "-daily-child"
            child["id"] = child_id
            child["nodes"][0]["config"]["cron"] = "0 0 1 1 *"
            child_worker = next(part for part in child["nodes"] if part["type"] == "codex")
            child_worker["config"]["workdir"] = str(workspace)
            server.put(f"/api/environments/{child_id}", child)
            cfg["env"] = child_id
        elif node["type"] == "approval":
            cfg["prompt"] = "Approve this test-only action in a temporary folder?"

    if template_id == "tpl-downloads-tidy":
        downloads = home / "Downloads"
        downloads.mkdir()
        old = downloads / "older-fixture.txt"
        old.write_text("safe test fixture", encoding="utf-8")
        stamp = time.time() - 10 * 86400
        os.utime(old, (stamp, stamp))
    elif template_id == "tpl-backup-check":
        backups = home / "Backups"
        backups.mkdir()
        old = backups / "old-fixture.zip"
        old.write_text("safe test fixture", encoding="utf-8")
        stamp = time.time() - 5 * 86400
        os.utime(old, (stamp, stamp))
    elif template_id == "tpl-web-change-watch":
        class Page(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                payload = b"<html><body>Glacier local template fixture</body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        page = socketserver.TCPServer(("127.0.0.1", 0), Page)
        page_thread = threading.Thread(target=page.serve_forever, daemon=True)
        page_thread.start()
        fetch = next(node for node in nodes.values() if node["type"] == "fetch_page")
        fetch["config"]["url"] = f"http://127.0.0.1:{page.server_address[1]}/"
        fetch["config"]["allowed_sites"] = "127.0.0.1"

    if template_id == "tpl-website-monitor":
        next(node for node in nodes.values() if node["type"] == "command")["config"]["cmd"] = "true"

    if template_id == "tpl-inbox-triage":
        decide_cfg = next(node for node in nodes.values() if node["type"] == "decide")["config"]
        decide_cfg["engine"] = "codex"
        decide_cfg.pop("model", None)
    if template_id == "tpl-test-and-fix":
        # Exercise the successful verification branch against a real small pytest
        # project, avoiding a repair request over an intentionally empty workspace.
        (workspace / "test_sample.py").write_text("def test_template_fixture():\n    assert 'glacier' == 'glacier'\n", encoding="utf-8")
        python = sys.executable
        for node in nodes.values():
            if node["type"] == "command" and "pytest" in node["config"].get("cmd", ""):
                node["config"]["cmd"] = f"'{python}' -m pytest -q"
    server.put(f"/api/environments/{env_id}", flow)
    run_id = server.post(f"/api/environments/{env_id}/run")["run_id"]
    deadline = time.time() + 360
    try:
        while time.time() < deadline:
            run = server.get(f"/api/runs/{run_id}")
            if run["status"] == "waiting":
                server.post(f"/api/runs/{run_id}/approve", {"node_id": run["waiting_on"], "approved": True})
            elif run["status"] in ("done", "failed", "rejected"):
                break
            time.sleep(0.25)
    finally:
        if template_id == "tpl-web-change-watch":
            page.shutdown()
            page_thread.join(timeout=2)
            page.server_close()
    if run["status"] != "done" and codex_needed and any("not signed in" in str(output).lower() for output in run["outputs"].values()):
        pytest.skip(f"{template_id} installed; Codex CLI is not signed in for this backend process")
    assert run["status"] == "done", f"{template_id} real-backend run failed: {run}"
    assert run_id in {row["run_id"] for row in server.get("/api/runs", params={"env_id": env_id})}
    if flow.get("acceptance"):
        assert run["verification"] and all(check["passed"] for check in run["verification"]), (template_id, run["verification"])
