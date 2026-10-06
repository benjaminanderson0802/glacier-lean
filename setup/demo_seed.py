"""Seeds two demo environments into a running Glacier backend (default http://localhost:8000) with slowed-down
steps so every state change is visible on the screen.  Usage: python setup/demo_seed.py [api_url]"""
import json, sys, urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def put(env):
    req = urllib.request.Request(f"{API}/api/environments/{env['id']}", data=json.dumps(env).encode(), method="PUT",
                                 headers={"Content-Type": "application/json"})
    print(env["id"], urllib.request.urlopen(req).read().decode())


def node(i, t, c, x, y):
    return {"id": i, "type": t, "config": c, "position": {"x": x, "y": y}}


def edge(k, s, t, l=""):
    return {"id": f"e{k}", "source": s, "target": t, "label": l}


put({"id": "demo-report", "name": "Demo: write report", "nodes": [
    node("gather", "command", {"cmd": "sleep 2; echo gathered 3 results"}, 0, 0),
    node("save", "note", {"path": "runs/demo-report-{run}.md", "template": "Demo report for run {run}: {summary}"}, 260, 0)],
    "edges": [edge(0, "gather", "save")]})

put({"id": "demo-loop", "name": "Demo: build, test, repeat", "nodes": [
    node("start", "command", {"cmd": "sleep 1; echo starting build"}, 0, 120),
    node("repeat", "loop", {"times": "3"}, 260, 120),
    node("build", "command", {"cmd": "sleep 2; echo build ok at $(date +%T)"}, 520, 0),
    node("test", "command", {"cmd": "sleep 2; echo 12 tests passed"}, 780, 0),
    node("report", "flow", {"env": "demo-report"}, 520, 260),
    node("passed", "check", {"expr": "exit_code == 0"}, 780, 260),
    node("ok", "approval", {"prompt": "Report written. Mark this release ready?"}, 1040, 200),
    node("log", "note", {"path": "runs/demo-loop-{run}.md", "template": "Demo run {run}: {summary}"}, 1300, 200),
    node("fix", "note", {"path": "runs/demo-fix-{run}.md", "template": "Report failed in run {run}"}, 1040, 340)],
    "edges": [edge(0, "start", "repeat"), edge(1, "repeat", "build", "again"), edge(2, "build", "test"),
              edge(3, "test", "repeat"), edge(4, "repeat", "report", "done"), edge(5, "report", "passed"),
              edge(6, "passed", "ok", "yes"), edge(7, "passed", "fix", "no"), edge(8, "ok", "log", "yes")]})
