"""Acceptance tests for the assistant chat stream and approval gated proposals."""
import json
import subprocess
import sys
import textwrap

import httpx

from conftest import Server


def _chat_server(tmp_path, monkeypatch):
    script = tmp_path / "planner.py"
    script.write_text(textwrap.dedent(f'''
        import json, sys
        args = sys.argv[1:]
        out = args[args.index("-o") + 1]
        if "FAIL" in args[-1]:
            sys.exit(1)
        node = {{"id":"backup","type":"command","config":[{{"key":"cmd","value":"tar -czf backup.tgz data"}}]}}
        if "INVALID_CRON" in args[-1]:
            node = {{"id":"schedule","type":"schedule","config":[{{"key":"cron","value":"not a cron"}}]}}
        result = {{"name":"Daily backup", "explanation":"Backs up files each day.",
          "nodes":[node],
          "edges":[], "acceptance":[{{"kind":"human","question":"Did the backup finish?","cmd":"","rubric":""}}]}}
        open(out,"w").write(json.dumps(result))
    '''))
    wrapper = tmp_path / "planner.sh"
    wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {script} \"$@\"\n")
    wrapper.chmod(0o755)
    monkeypatch.setenv("GLACIER_PLANNER_BIN", str(wrapper))
    chat_script = tmp_path / "chat.py"
    chat_script.write_text(textwrap.dedent('''
        import json, sys
        args=sys.argv[1:]; out=args[args.index("-o")+1]; prompt=args[-1]
        if "FAIL" in prompt: sys.exit(1)
        open(out,"w").write(json.dumps({"reply":"I can help with that.","automation":False}))
    '''))
    chat_wrapper = tmp_path / "chat.sh"
    chat_wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {chat_script} \"$@\"\n")
    chat_wrapper.chmod(0o755)
    monkeypatch.setenv("GLACIER_CHAT_BIN", str(chat_wrapper))
    home = tmp_path / "home"
    home.mkdir()
    return Server(home).start()


def _events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def _proposal(server):
    events = _events(httpx.post(server.url + "/api/assistant/chat", json={"message": "make me a daily backup"}, timeout=30))
    args = next(event["delta"] for event in events if event["type"] == "TOOL_CALL_ARGS")
    return json.loads(args)


def test_chat_stream_has_ordered_ag_ui_events(tmp_path, monkeypatch):
    server = _chat_server(tmp_path, monkeypatch)
    try:
        response = httpx.post(server.url + "/api/assistant/chat", json={"message": "Hello"}, timeout=30)
        assert response.status_code == 200
        events = _events(response)
        names = [event["type"] for event in events]
        assert names[0] == "RUN_STARTED"
        assert names.index("TEXT_MESSAGE_START") < names.index("TEXT_MESSAGE_CONTENT") < names.index("TEXT_MESSAGE_END") < names.index("RUN_FINISHED")
    finally:
        server.stop()


def test_automation_chat_proposes_flow_and_does_not_save(tmp_path, monkeypatch):
    server = _chat_server(tmp_path, monkeypatch)
    try:
        response = httpx.post(server.url + "/api/assistant/chat", json={"message": "make me a daily backup"}, timeout=30)
        events = _events(response)
        tool = next(event for event in events if event["type"] == "TOOL_CALL_START")
        assert tool["toolCallName"] == "propose_flow"
        assert any(event["type"] == "TOOL_CALL_ARGS" and "acceptance" in json.dumps(event) for event in events)
        assert server.get("/api/environments") == []
    finally:
        server.stop()


def test_apply_requires_explicit_approval(tmp_path, monkeypatch):
    server = _chat_server(tmp_path, monkeypatch)
    try:
        proposal = _proposal(server)
        missing = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply", json={}, timeout=30)
        assert missing.status_code == 422
        response = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                              json={"approve": False}, timeout=30)
        assert response.status_code == 200 and response.json() == {"discarded": True}
        assert server.get("/api/environments") == []
    finally:
        server.stop()


def test_approved_proposal_is_saved_once_as_assistant_and_can_be_undone(tmp_path, monkeypatch):
    server = _chat_server(tmp_path, monkeypatch)
    try:
        proposal = _proposal(server)
        path = f"environments/{proposal['flow']['id']}.json"
        response = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                              json={"approve": True}, timeout=30)
        assert response.status_code == 200 and response.json()["saved"] is True
        repo = server.home + "/vault"
        commits = subprocess.run(["git", "log", "--format=%H", "--", path], cwd=repo,
                                 capture_output=True, text=True, check=True).stdout.splitlines()
        assert len(commits) == 1
        author = subprocess.run(["git", "show", "-s", "--format=%an", commits[0]], cwd=repo,
                                capture_output=True, text=True, check=True).stdout.strip()
        assert author == "assistant"
        message = subprocess.run(["git", "show", "-s", "--format=%s", commits[0]], cwd=repo,
                                 capture_output=True, text=True, check=True).stdout.strip()
        assert proposal["conversation_id"] in message
        undo = httpx.post(server.url + f"/api/runs/{proposal['conversation_id']}/undo", timeout=30)
        assert undo.status_code == 200
        assert server.get("/api/environments") == []
    finally:
        server.stop()


def test_invalid_proposal_is_refused_with_same_message_as_environment_save(tmp_path, monkeypatch):
    server = _chat_server(tmp_path, monkeypatch)
    try:
        events = _events(httpx.post(server.url + "/api/assistant/chat",
                                    json={"message": "make me INVALID_CRON daily backup"}, timeout=30))
        proposal = json.loads(next(event["delta"] for event in events if event["type"] == "TOOL_CALL_ARGS"))
        flow = proposal["flow"]
        put = httpx.put(server.url + f"/api/environments/{flow['id']}", json=flow, timeout=30)
        apply = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                           json={"approve": True}, timeout=30)
        assert put.status_code == apply.status_code == 400
        assert put.json()["detail"] == apply.json()["detail"]
        assert server.get("/api/environments") == []
    finally:
        server.stop()


def test_model_failure_returns_plain_run_error(server):
    events = _events(httpx.post(server.url + "/api/assistant/chat", json={"message": "FAIL"}, timeout=30))
    assert events[-1]["type"] == "RUN_ERROR"
    assert isinstance(events[-1].get("message"), str) and events[-1]["message"]
