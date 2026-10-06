import os, json, time, subprocess
import pytest
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
