"""The assistant turns a goal into a proposed flow with checks; it never saves or runs anything itself."""
import json, sys, textwrap
import httpx
from conftest import Server

PLANNER = textwrap.dedent('''
    import json, os, sys
    args = sys.argv[1:]
    out = args[args.index("-o") + 1]
    prompt = args[-1]
    good = {"name": "Daily site check", "explanation": "Checks the site and asks you before alerting.",
            "nodes": [{"id": "c", "type": "command", "config": [{"key": "cmd", "value": "curl -sf https://example.org"}]},
                      {"id": "k", "type": "check", "config": [{"key": "expr", "value": "exit_code == 0"}]},
                      {"id": "n", "type": "note", "config": [{"key": "path", "value": "runs/{run}.md"}, {"key": "template", "value": "{summary}"}]}],
            "edges": [{"source": "c", "target": "k", "label": ""}, {"source": "k", "target": "n", "label": "yes"}],
            "acceptance": [{"kind": "command", "cmd": "test -n ok", "question": "", "rubric": ""}]}
    bad = json.loads(json.dumps(good)); bad["edges"][1]["label"] = "maybe"; bad["nodes"][0]["config"].append({"key": "colour", "value": "red"})
    mode = os.environ.get("FAKE_PLANNER", "good")
    answer = good if mode == "good" or (mode == "repair" and "previous plan had these problems" in prompt) else bad
    open(out, "w").write(json.dumps(answer))
''')


def _server(tmp_path, monkeypatch, mode):
    script = tmp_path / "planner.py"; script.write_text(PLANNER)
    wrapper = tmp_path / "planner.sh"; wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {script} \"$@\"\n"); wrapper.chmod(0o755)
    monkeypatch.setenv("GLACIER_PLANNER_BIN", str(wrapper)); monkeypatch.setenv("FAKE_PLANNER", mode)
    home = tmp_path / "home"; home.mkdir()
    return Server(home).start()


def test_goal_becomes_a_reviewable_flow_with_checks(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "good")
    try:
        r = s.post("/api/assistant/plan", {"goal": "Check my website every day"})
        assert r["problems"] == [] and r["explanation"]
        f = r["flow"]
        assert f["goal"] == "Check my website every day" and f["acceptance"] == [{"kind": "command", "cmd": "test -n ok"}]
        assert f["nodes"][0]["config"] == {"cmd": "curl -sf https://example.org"} and all("position" in n for n in f["nodes"])
        assert s.get("/api/environments") == []  # proposing saves nothing
        assert s.put(f"/api/environments/{f['id']}", f)["saved"] is True  # the owner saves it through the normal API
    finally:
        s.stop()


def test_invalid_plan_gets_one_repair_attempt(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "repair")
    try:
        r = s.post("/api/assistant/plan", {"goal": "Check my website"})
        assert r["problems"] == [], r
    finally:
        s.stop()


def test_problems_are_shown_when_repair_fails(tmp_path, monkeypatch):
    s = _server(tmp_path, monkeypatch, "bad")
    try:
        r = s.post("/api/assistant/plan", {"goal": "Check my website"})
        assert any("maybe" in p for p in r["problems"]) and any("colour" in p for p in r["problems"]), r
    finally:
        s.stop()


def test_empty_goal_rejected(server):
    assert httpx.post(server.url + "/api/assistant/plan", json={"goal": "  "}, timeout=30).status_code == 400
