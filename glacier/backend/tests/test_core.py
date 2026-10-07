import os, json, time, subprocess
import pytest, httpx
from websockets.sync.client import connect
from conftest import env


def git_log(home, path):
    return subprocess.run(["git", "log", "--format=%h", "--", path], cwd=os.path.join(home, "vault"),
                          capture_output=True, text=True, check=True).stdout.split()


def test_save_environment_commits_to_vault(server):
    e = env("save-me", [("n1", "command", {"cmd": "true"})], [])
    res = server.put("/api/environments/save-me", e)
    assert res["saved"] is True and res["commit"]
    commits = git_log(server.home, "environments/save-me.json")
    assert len(commits) == 1 and res["commit"].startswith(commits[0][:7])
    assert server.get("/api/environments") == [{"id": "save-me", "name": "Save Me"}]
    assert server.get("/api/environments/save-me") == e
    e["name"] = "Renamed"
    server.put("/api/environments/save-me", e)
    assert len(git_log(server.home, "environments/save-me.json")) == 2


def test_command_check_note_run(server):
    e = env("happy", [("c", "command", {"cmd": "echo hello"}), ("k", "check", {"expr": "exit_code == 0"}),
                      ("n", "note", {"path": "runs/{env}-{run}.md", "template": "Run {run} of {env}: {summary}"}),
                      ("bad", "note", {"path": "runs/never.md", "template": "x"})],
            [("c", "k", ""), ("k", "n", "yes"), ("k", "bad", "no")])
    server.put("/api/environments/happy", e)
    run_id = server.post("/api/environments/happy/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "done" and run["waiting_on"] is None
    assert run["node_states"] == {"c": "done", "k": "done", "n": "done", "bad": "skipped"}
    assert "hello" in run["outputs"]["c"]
    path = f"runs/happy-{run_id}.md"
    assert path in server.get("/api/vault/notes")
    body = server.get("/api/vault/note", params={"path": path})["body"]
    assert body.startswith(f"Run {run_id} of happy:")
    assert git_log(server.home, path)
    assert [r["run_id"] for r in server.get("/api/runs", params={"env_id": "happy"})] == [run_id]


APPROVAL_ENV = env("needs-ok", [("c", "command", {"cmd": "echo boom; exit 3"}), ("k", "check", {"expr": "exit_code == 0"}),
                                ("a", "approval", {"prompt": "Tests failed. Continue?"}),
                                ("n", "note", {"path": "runs/{run}.md", "template": "approved {run}"})],
                   [("c", "k", ""), ("k", "n", "yes"), ("k", "a", "no"), ("a", "n", "yes")])


def test_failing_command_goes_to_approval_then_note(server):
    server.put("/api/environments/needs-ok", APPROVAL_ENV)
    run_id = server.post("/api/environments/needs-ok/run")["run_id"]
    run = server.wait_run(run_id, ("waiting",))
    assert run["waiting_on"] == "a" and run["node_states"]["a"] == "waiting"
    assert run["node_states"]["c"] == "failed" and "boom" in run["outputs"]["c"]
    assert run["node_states"]["n"] == "pending"
    assert server.post(f"/api/runs/{run_id}/approve", {"node_id": "a", "approved": True}) == {"ok": True}
    run = server.wait_run(run_id)
    assert run["status"] == "done" and run["node_states"]["n"] == "done" and run["node_states"]["a"] == "done"
    assert server.get("/api/vault/note", params={"path": f"runs/{run_id}.md"})["body"] == f"approved {run_id}"


def test_crash_mid_run_resumes_without_rerunning_finished_nodes(make_server, tmp_path):
    marks = tmp_path / "marks"; marks.mkdir()
    e = env("crashy", [("c1", "command", {"cmd": f"echo x >> {marks}/c1"}),
                       ("slow", "command", {"cmd": f"echo x >> {marks}/slow; sleep 5"}),
                       ("c2", "command", {"cmd": f"echo x >> {marks}/c2"})],
            [("c1", "slow", ""), ("slow", "c2", "")])
    s = make_server().start()
    s.put("/api/environments/crashy", e)
    run_id = s.post("/api/environments/crashy/run")["run_id"]
    for _ in range(100):
        if (marks / "slow").exists():
            break
        time.sleep(0.1)
    assert s.get(f"/api/runs/{run_id}")["node_states"]["slow"] == "running"
    s.kill()
    assert not (marks / "c2").exists()
    s.start()
    run = s.wait_run(run_id, timeout=40)
    assert run["status"] == "done" and set(run["node_states"].values()) == {"done"}
    assert (marks / "c1").read_text() == "x\n"          # finished step was not re-run
    assert (marks / "slow").read_text() == "x\nx\n"     # interrupted step re-ran once
    assert (marks / "c2").read_text() == "x\n"


def test_approval_survives_restart(make_server):
    s = make_server().start()
    s.put("/api/environments/needs-ok", APPROVAL_ENV)
    run_id = s.post("/api/environments/needs-ok/run")["run_id"]
    s.wait_run(run_id, ("waiting",))
    s.kill()
    s.start()
    run = s.get(f"/api/runs/{run_id}")
    assert run["status"] == "waiting" and run["waiting_on"] == "a"
    s.post(f"/api/runs/{run_id}/approve", {"node_id": "a", "approved": True})
    run = s.wait_run(run_id)
    assert run["status"] == "done" and run["node_states"]["n"] == "done"


def test_schedule_creates_runs(server):
    e = env("ticker", [("s", "schedule", {"cron": "*/2 * * * * *"}), ("c", "command", {"cmd": "echo tick"})], [("s", "c", "")])
    server.put("/api/environments/ticker", e)
    deadline, runs = time.time() + 20, []
    while time.time() < deadline:
        runs = [r for r in server.get("/api/runs", params={"env_id": "ticker"}) if r["status"] == "done"]
        if len(runs) >= 2:
            break
        time.sleep(0.5)
    assert len(runs) >= 2
    assert server.get(f"/api/runs/{runs[0]['run_id']}")["node_states"] == {"s": "done", "c": "done"}
    # removing the schedule node deletes the schedule
    server.put("/api/environments/ticker", env("ticker", [("c", "command", {"cmd": "echo tick"})], []))
    time.sleep(3)
    before = len(server.get("/api/runs", params={"env_id": "ticker"}))
    time.sleep(5)
    assert len(server.get("/api/runs", params={"env_id": "ticker"})) == before


def test_websocket_receives_node_events(server):
    e = env("ws", [("c", "command", {"cmd": "echo hi"}), ("n", "note", {"path": "runs/ws.md", "template": "{summary}"})], [("c", "n", "")])
    server.put("/api/environments/ws", e)
    with connect(server.url.replace("http", "ws") + "/api/events") as ws:
        time.sleep(0.3)
        run_id = server.post("/api/environments/ws/run")["run_id"]
        seen = []
        while ("n", "done") not in seen:
            msg = json.loads(ws.recv(timeout=15))
            assert msg["run_id"] == run_id and msg["env_id"] == "ws"
            seen.append((msg["node_id"], msg["state"]))
            if (msg["node_id"], msg["state"]) == ("c", "done"):
                assert "hi" in msg["output"]
    assert seen == [("c", "running"), ("c", "done"), ("n", "running"), ("n", "done")]


def test_codex_node_output_saved(server):
    server.put("/api/environments/cx", env("cx", [("x", "codex", {"prompt": "fix the tests in {env}", "sandbox": "read-only", "model": "gpt-5"})], []))
    run = server.wait_run(server.post("/api/environments/cx/run")["run_id"])
    assert run["status"] == "done" and run["node_states"] == {"x": "done"}
    out = run["outputs"]["x"]
    assert out.startswith("codex exit 0\n")
    assert "did: fix the tests in cx [sandbox=read-only cwd=cx model=gpt-5]" in out  # default workdir workspaces/<env>
    assert os.path.isdir(os.path.join(server.home, "workspaces", "cx"))


def test_codex_prev_output_substitution(server):
    e = env("cxprev", [("c", "command", {"cmd": "echo hello-prev"}), ("x", "codex", {"prompt": "summarize <{prev_output}> run {run}"})],
            [("c", "x", "")])
    server.put("/api/environments/cxprev", e)
    run_id = server.post("/api/environments/cxprev/run")["run_id"]
    run = server.wait_run(run_id)
    assert run["status"] == "done"
    assert f"did: summarize <hello-prev\n> run {run_id} [sandbox=workspace-write" in run["outputs"]["x"]


def test_failing_codex_routes_check_no(server):
    e = env("cxfail", [("x", "codex", {"prompt": "please FAIL"}), ("k", "check", {"expr": "exit_code == 0"}),
                       ("yes", "note", {"path": "runs/yes.md", "template": "y"}), ("no", "note", {"path": "runs/no.md", "template": "n"})],
            [("x", "k", ""), ("k", "yes", "yes"), ("k", "no", "no")])
    server.put("/api/environments/cxfail", e)
    run = server.wait_run(server.post("/api/environments/cxfail/run")["run_id"])
    assert run["node_states"] == {"x": "failed", "k": "done", "yes": "skipped", "no": "done"}
    assert run["outputs"]["x"].startswith("codex exit 1\n") and run["outputs"]["k"] == "no"
    assert run["status"] == "done"


def test_codex_not_signed_in_fails_with_hint(server):
    server.put("/api/environments/cxauth", env("cxauth", [("x", "codex", {"prompt": "NOAUTH"})], []))
    run = server.wait_run(server.post("/api/environments/cxauth/run")["run_id"])
    assert run["status"] == "failed" and run["node_states"]["x"] == "failed"
    assert "Codex not signed in — run: codex login --device-auth" in run["outputs"]["x"]


def test_save_rejects_unknown_node_type_but_accepts_codex(server):
    import httpx
    assert server.put("/api/environments/ok", env("ok", [("x", "codex", {"prompt": "hi"})], []))["saved"]
    r = httpx.put(server.url + "/api/environments/bad", json=env("bad", [("x", "robot", {})], []))
    assert r.status_code == 400 and "robot" in r.text


def test_codex_streams_live_log_while_running(make_server, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_DELAY", "1.5")
    s = make_server().start()
    s.put("/api/environments/cxlive", env("cxlive", [("x", "codex", {"prompt": "slow job"})], []))
    run_id = s.post("/api/environments/cxlive/run")["run_id"]
    live = None
    for _ in range(80):
        run = s.get(f"/api/runs/{run_id}")
        if run["node_states"]["x"] == "running" and run["outputs"].get("x"):
            live = run["outputs"]["x"]; break
        time.sleep(0.1)
    assert live and "thread.started" in live and "codex exit" not in live
    assert s.wait_run(run_id)["outputs"]["x"].startswith("codex exit 0\n")


def test_graceful_shutdown_with_live_clients(server):
    """SIGTERM must stop the backend in under 5 s even while screens are connected to live updates."""
    import signal
    clients = [connect(server.url.replace("http", "ws") + "/api/events") for _ in range(2)]
    time.sleep(0.3)
    t0 = time.time()
    server.proc.send_signal(signal.SIGTERM)
    try:
        code = server.proc.wait(10)
    except subprocess.TimeoutExpired:
        code = None
    took = time.time() - t0
    for c in clients:
        try:
            c.close()
        except Exception:
            pass
    assert code is not None and took < 5, f"backend still running {took:.1f}s after SIGTERM"
    # uvicorn re-raises the signal after a clean shutdown, so check its log rather than the exit code
    server.log.flush()
    log = open(os.path.join(server.home, "server.log")).read()
    assert "Application shutdown complete" in log, log[-800:]


def test_loop_runs_n_times_then_exits(server):
    ticks = os.path.join(server.home, "ticks.txt")
    e = env("looper", [("s", "command", {"cmd": "echo start"}), ("L", "loop", {"times": 3}),
                       ("c", "command", {"cmd": f"echo tick >> {ticks}"}),
                       ("n", "note", {"path": "runs/{run}.md", "template": "looped {run}"})],
            [("s", "L", ""), ("L", "c", "again"), ("c", "L", ""), ("L", "n", "done")])
    server.put("/api/environments/looper", e)
    run = server.wait_run(server.post("/api/environments/looper/run")["run_id"])
    assert run["status"] == "done", run
    assert open(ticks).read().split() == ["tick"] * 3
    assert run["node_states"]["L"] == "done" and "3 of 3" in run["outputs"]["L"]
    assert run["node_states"]["n"] == "done"


def test_runaway_cycle_stops_at_step_limit(server):
    e = env("runaway", [("a", "command", {"cmd": "true"}), ("b", "command", {"cmd": "true"})], [("a", "b", ""), ("b", "a", "")])
    e["max_steps"] = 10
    server.put("/api/environments/runaway", e)
    run = server.wait_run(server.post("/api/environments/runaway/run")["run_id"])
    assert run["status"] == "failed", run


def test_sub_flow_runs_child_and_shows_its_states(server):
    server.put("/api/environments/child", env("child", [("c", "command", {"cmd": "echo child-ran"}),
                                                        ("n", "note", {"path": "runs/child-{run}.md", "template": "{summary}"})], [("c", "n", "")]))
    server.put("/api/environments/parent", env("parent", [("f", "flow", {"env": "child"}), ("k", "check", {"expr": "exit_code == 0"}),
                                                          ("ok", "note", {"path": "runs/p-{run}.md", "template": "ok"}),
                                                          ("bad", "note", {"path": "runs/never.md", "template": "x"})],
                                               [("f", "k", ""), ("k", "ok", "yes"), ("k", "bad", "no")]))
    run = server.wait_run(server.post("/api/environments/parent/run")["run_id"])
    assert run["status"] == "done", run
    assert run["node_states"] == {"f": "done", "k": "done", "ok": "done", "bad": "skipped"}
    child_runs = server.get("/api/runs", params={"env_id": "child"})
    assert len(child_runs) == 1 and child_runs[0]["run_id"] in run["outputs"]["f"]
    child = server.get(f"/api/runs/{child_runs[0]['run_id']}")
    assert child["status"] == "done" and child["node_states"] == {"c": "done", "n": "done"}


def test_failing_sub_flow_routes_check_no(server):
    server.put("/api/environments/bad-child", env("bad-child", [("c", "command", {"cmd": "exit 3"})], []))
    server.put("/api/environments/p2", env("p2", [("f", "flow", {"env": "bad-child"}), ("k", "check", {"expr": "exit_code == 0"}),
                                                  ("ok", "note", {"path": "runs/never.md", "template": "x"}),
                                                  ("fix", "note", {"path": "runs/fix-{run}.md", "template": "child failed"})],
                                           [("f", "k", ""), ("k", "ok", "yes"), ("k", "fix", "no")]))
    run = server.wait_run(server.post("/api/environments/p2/run")["run_id"])
    assert run["status"] == "done" and run["node_states"]["f"] == "failed" and run["node_states"]["fix"] == "done", run


def test_self_calling_flow_is_depth_limited(server):
    server.put("/api/environments/selfie", env("selfie", [("f", "flow", {"env": "selfie"})], []))
    run = server.wait_run(server.post("/api/environments/selfie/run")["run_id"], timeout=60)
    assert run["status"] == "failed"
    deepest = [r for r in server.get("/api/runs", params={"env_id": "selfie"}) if "nested" in (r.get("outputs") or {}).get("f", "")
               or "nested" in server.get(f"/api/runs/{r['run_id']}")["outputs"].get("f", "")]
    assert deepest, "no run reports the nesting limit"


def test_node_types_catalog_served_and_enforced(server):
    cat = server.get("/api/node-types")
    kinds = [t["type"] for t in cat]
    assert kinds[:9] == ["schedule", "command", "codex", "check", "approval", "decide", "note", "loop", "flow"]  # step plug-ins come after
    for t in cat:
        assert t["label"] and isinstance(t["fields"], list) and (t["branches"] is None or len(t["branches"]) == 2)
        assert t["branches"] is None or "branches_from" not in t
    assert {t["type"]: t["branches"] for t in cat}["loop"] == ["again", "done"]
    r = httpx.put(server.url + "/api/environments/bad", json=env("bad", [("x", "teleport", {})], []), timeout=30)
    assert r.status_code == 400


def _counter_cmd(path, succeed_at):
    return f'n=$(cat {path} 2>/dev/null || echo 0); n=$((n+1)); echo $n > {path}; echo try $n; [ $n -ge {succeed_at} ]'


def test_command_retries_then_succeeds(server):
    f = os.path.join(server.home, "count1")
    server.put("/api/environments/retry-ok", env("retry-ok", [("c", "command", {"cmd": _counter_cmd(f, 3), "retries": "2"})], []))
    run = server.wait_run(server.post("/api/environments/retry-ok/run")["run_id"])
    assert run["status"] == "done" and run["node_states"]["c"] == "done", run
    assert open(f).read().strip() == "3" and "attempt 3 of 3" in run["outputs"]["c"]


def test_command_retries_exhausted_fails(server):
    f = os.path.join(server.home, "count2")
    server.put("/api/environments/retry-bad", env("retry-bad", [("c", "command", {"cmd": _counter_cmd(f, 99), "retries": "1"})], []))
    run = server.wait_run(server.post("/api/environments/retry-bad/run")["run_id"])
    assert run["status"] == "failed" and open(f).read().strip() == "2", run


def test_command_timeout(server):
    server.put("/api/environments/slow", env("slow", [("c", "command", {"cmd": "sleep 20", "timeout": "1"})], []))
    t0 = time.time()
    run = server.wait_run(server.post("/api/environments/slow/run")["run_id"])
    assert run["status"] == "failed" and time.time() - t0 < 10 and "timed out after 1s" in run["outputs"]["c"], run


def test_failed_run_sends_exactly_one_alert(tmp_path, monkeypatch):
    """A broken run (including a failing sub-flow inside it) sends one plain-language alert; a good run sends none."""
    import http.server, threading
    from conftest import Server, free_port
    got = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200); self.end_headers()

        def log_message(self, *a):
            pass

    port = free_port()
    hs = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=hs.serve_forever, daemon=True).start()
    monkeypatch.setenv("GLACIER_ALERT_URLS", f"json://127.0.0.1:{port}/")
    s = Server(tmp_path).start()
    try:
        s.put("/api/environments/kid", env("kid", [("c", "command", {"cmd": "echo boom; exit 4"})], []))
        s.put("/api/environments/parent-a", env("parent-a", [("f", "flow", {"env": "kid"})], []))
        s.put("/api/environments/fine", env("fine", [("c", "command", {"cmd": "echo ok"})], []))
        assert s.wait_run(s.post("/api/environments/fine/run")["run_id"])["status"] == "done"
        run = s.wait_run(s.post("/api/environments/parent-a/run")["run_id"])
        assert run["status"] == "failed"
        deadline = time.time() + 20
        while not got and time.time() < deadline:
            time.sleep(0.25)
        time.sleep(2)  # make sure no second alert follows
        assert len(got) == 1, got
        assert "parent-a" in got[0]["title"] and run["run_id"] in got[0]["message"], got[0]
    finally:
        s.stop(); hs.shutdown()


def _fake_ollama(answer_for):
    """Tiny stand-in for Ollama's /api/chat: answer_for(prompt) -> choice string. Returns (url, seen_requests, server)."""
    import http.server, threading
    from conftest import free_port
    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            out = json.dumps({"message": {"content": json.dumps({"choice": answer_for(body["messages"][0]["content"])})}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)

        def log_message(self, *a):
            pass

    port = free_port()
    hs = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=hs.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", seen, hs


DECIDE_ENV = env("triage", [("t", "command", {"cmd": "echo 'customer: I want a refund for order 12'"}),
                            ("d", "decide", {"question": "Which team should handle this ticket?", "options": "Billing, Tech support, Other", "engine": "local"}),
                            ("b", "note", {"path": "runs/billing-{run}.md", "template": "billing"}),
                            ("s", "note", {"path": "runs/tech-{run}.md", "template": "tech"})],
                 [("t", "d", ""), ("d", "b", "Billing"), ("d", "s", "Tech support")])


def test_decide_step_follows_chosen_branch(tmp_path, monkeypatch):
    from conftest import Server
    url, seen, hs = _fake_ollama(lambda prompt: "billing" if "refund" in prompt else "Other")
    monkeypatch.setenv("GLACIER_OLLAMA_URL", url)
    s = Server(tmp_path).start()
    try:
        s.put("/api/environments/triage", DECIDE_ENV)
        run = s.wait_run(s.post("/api/environments/triage/run")["run_id"])
        assert run["status"] == "done", run
        assert run["node_states"] == {"t": "done", "d": "done", "b": "done", "s": "skipped"}, run
        assert "Billing" in run["outputs"]["d"] and "local model" in run["outputs"]["d"]
        req = seen[0]
        assert req["format"]["properties"]["choice"]["enum"] == ["Billing", "Tech support", "Other"]  # output constrained to the options
        assert "refund" in req["messages"][0]["content"]  # previous step's output is the context
    finally:
        s.stop(); hs.shutdown()


def test_decide_rejects_answers_outside_the_options(tmp_path, monkeypatch):
    from conftest import Server
    url, _, hs = _fake_ollama(lambda prompt: "pizza")
    monkeypatch.setenv("GLACIER_OLLAMA_URL", url)
    s = Server(tmp_path).start()
    try:
        s.put("/api/environments/triage", DECIDE_ENV)
        run = s.wait_run(s.post("/api/environments/triage/run")["run_id"])
        assert run["status"] == "failed" and run["node_states"]["d"] == "failed"
        assert "not one of the options" in run["outputs"]["d"]
    finally:
        s.stop(); hs.shutdown()


def test_decide_needs_two_options(server):
    e = env("one-opt", [("d", "decide", {"question": "Pick", "options": "only", "engine": "local"})], [])
    server.put("/api/environments/one-opt", e)
    run = server.wait_run(server.post("/api/environments/one-opt/run")["run_id"])
    assert run["status"] == "failed" and "at least 2 options" in run["outputs"]["d"]


def test_decide_catalog_entry(server):
    t = {x["type"]: x for x in server.get("/api/node-types")}["decide"]
    assert t["branches"] is None and t["branches_from"] == "options"
    assert [f["key"] for f in t["fields"]][:3] == ["question", "options", "engine"]
