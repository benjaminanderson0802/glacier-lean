"""Ask approval-to-run and chat result reporting acceptance tests."""
import json
import os
import sys
import textwrap
import time
import uuid

import httpx
import shell_commands

from conftest import Server


def _server(tmp_path, monkeypatch):
    chat = tmp_path / "chat.py"
    chat.write_text(textwrap.dedent('''
        import json, sys
        args = sys.argv[1:]
        out = args[args.index("-o") + 1]
        prompt = args[-1]
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"reply":"Okay.", "automation":False}, f)
    '''), encoding="utf-8")
    chat_command = chat
    if os.name != "nt":
        chat_command = tmp_path / "chat.sh"
        invoke = shell_commands.executable_invocation(sys.executable, str(chat))
        chat_command.write_text("#!/bin/sh\nexec " + " ".join(f'"{part}"' for part in invoke) + " \"$@\"\n", encoding="utf-8")
        chat_command.chmod(0o755)
    monkeypatch.setenv("GLACIER_CHAT_BIN", str(chat_command))
    monkeypatch.setenv("GLACIER_ASK_ROUTE", "codex")
    planner = tmp_path / "planner.py"
    planner.write_text(textwrap.dedent('''
        import json, sys
        args = sys.argv[1:]
        out = args[args.index("-o") + 1]
        prompt = args[-1]
        plan = {"name":"Daily backup", "explanation":"Backs up files each day.",
                "nodes":[{"id":"backup", "type":"command", "config":[
                    {"key":"cmd", "value":"echo chat-secret-123"}]}], "edges":[],
                "acceptance":[{"kind":"command", "cmd":"true", "question":"", "rubric":""}]}
        with open(out, "w", encoding="utf-8") as f:
            json.dump(plan, f)
    '''), encoding="utf-8")
    planner_command = planner
    if os.name != "nt":
        planner_command = tmp_path / "planner.sh"
        invoke = shell_commands.executable_invocation(sys.executable, str(planner))
        planner_command.write_text("#!/bin/sh\nexec " + " ".join(f'"{part}"' for part in invoke) + " \"$@\"\n", encoding="utf-8")
        planner_command.chmod(0o755)
    monkeypatch.setenv("GLACIER_PLANNER_BIN", str(planner_command))
    home = tmp_path / "home"
    home.mkdir()
    return Server(home).start()


def _events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def _proposal(server):
    conv = str(uuid.uuid4())
    events = _events(httpx.post(server.url + "/api/assistant/chat",
                                json={"conversation_id": conv, "message":"automate a daily backup"}, timeout=30))
    proposal = json.loads(next(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS"))
    return conv, proposal


def test_approved_run_now_starts_one_and_lists_run_and_appends_result_once(tmp_path, monkeypatch):
    server = _server(tmp_path, monkeypatch)
    try:
        conv, proposal = _proposal(server)
        before = server.get("/api/runs")
        response = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                              json={"approve":True, "run_now":True}, timeout=30)
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        assert len(server.get("/api/runs")) == len(before) + 1
        run = server.get(f"/api/runs/{run_id}")
        assert run["author"] == "assistant"
        deadline = time.time() + 10
        while time.time() < deadline and server.get(f"/api/runs/{run_id}")["status"] == "running":
            time.sleep(0.05)
        listed = server.get(f"/api/assistant/conversations/{conv}/runs")
        assert [row["run_id"] for row in listed] == [run_id]
        assert listed[0]["status"] == "done"

        note = server.get("/api/assistant/conversations/" + conv)["messages"]
        result_lines = [item["text"] for item in note if "finished" in item["text"]]
        assert len(result_lines) == 1
        assert "Daily backup finished" in " ".join(result_lines)
    finally:
        server.stop()


def test_run_my_exact_name_requires_approval_and_reject_starts_nothing(tmp_path, monkeypatch):
    server = _server(tmp_path, monkeypatch)
    try:
        _, proposal = _proposal(server)
        saved = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                           json={"approve":True}, timeout=30)
        assert saved.status_code == 200
        before = server.get("/api/runs")
        conv = str(uuid.uuid4())
        events = _events(httpx.post(server.url + "/api/assistant/chat",
                                    json={"conversation_id":conv, "message":"run my Daily backup now"}, timeout=30))
        call = next(e for e in events if e["type"] == "TOOL_CALL_START")
        assert call["toolCallName"] == "propose_run"
        proposal = json.loads(next(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS"))
        assert proposal["explanation"] == "Run Daily backup now?"
        rejected = httpx.post(server.url + f"/api/assistant/proposals/{proposal['id']}/apply",
                              json={"approve":False}, timeout=30)
        assert rejected.json() == {"discarded":True}
        assert server.get("/api/runs") == before
    finally:
        server.stop()


def test_run_my_ambiguous_close_name_asks_which(tmp_path, monkeypatch):
    server = _server(tmp_path, monkeypatch)
    try:
        for flow_id, name in (("backup-one", "Daily backup"), ("backup-two", "Daily backup copy")):
            flow = {"id":flow_id, "name":name, "goal":"backup", "nodes":[], "edges":[], "acceptance":[]}
            response = httpx.put(server.url + f"/api/environments/{flow_id}", json=flow, timeout=30)
            assert response.status_code == 200
        before = server.get("/api/runs")
        response = httpx.post(server.url + "/api/assistant/chat",
                              json={"message":"run my Daily backu now"}, timeout=30)
        events = _events(response)
        assert not any(e["type"] == "TOOL_CALL_START" for e in events)
        text = " ".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
        assert "Which one" in text
        assert "Daily backup" in text and "Daily backup copy" in text
        assert server.get("/api/runs") == before
    finally:
        server.stop()


def test_chat_result_line_is_redacted_before_note_write(tmp_path, monkeypatch):
    import runner
    import run_explain
    import routes.assistant_chat as assistant_chat
    import secrets_store
    import store
    import vault

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    vault.init(str(tmp_path / "vault"))
    assistant_chat._append_conversation(conversation_id := str(uuid.uuid4()), "Start", "Ready")
    store.init(str(tmp_path / "runs.sqlite"))
    run_id = "chat-report"
    graph = {"_assistant_conversation_id":conversation_id, "name":"Daily backup", "nodes":[], "acceptance":[]}
    store.create_run(run_id, "backup", graph)
    store.set_run(run_id, "done")
    monkeypatch.setattr(run_explain, "explain_run", lambda _: {"summary":"Daily backup finished: private-value."})
    monkeypatch.setattr(secrets_store, "redact", lambda text: text.replace("private-value", "[secret token]"))
    runner.finish_run.__wrapped__("backup", run_id, "done")
    note = vault.read_note(f"conversations/{conversation_id}.md")
    assert "private-value" not in note
    assert note.count("[secret token]") == 1
