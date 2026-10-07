import time

import httpx

from conftest import raw_httpx
from conftest import env as make_env


def rpc(server, method, params, request_id="test-1"):
    response = httpx.post(server.url + "/a2a", json={"jsonrpc": "2.0", "id": request_id,
                                                     "method": method, "params": params}, timeout=30)
    return response.status_code, response.json()


def test_card_lists_only_shareable_flows(server):
    public = make_env("public", [("echo", "command", {"cmd": "echo shared"})], [])
    private = make_env("private", [("echo", "command", {"cmd": "echo secret"})], [])
    public["share_a2a"] = True
    server.put("/api/environments/public", public)
    server.put("/api/environments/private", private)
    card = server.get("/.well-known/agent-card.json")
    skills = card["skills"]
    assert [skill["id"] for skill in skills] == ["public"]
    assert skills[0]["description"]


def test_a2a_requires_engine_token(server):
    response = raw_httpx["post"](server.url + "/a2a", json={"jsonrpc": "2.0", "id": 1,
        "method": "tasks/get", "params": {"id": "unknown"}}, timeout=30)
    assert response.status_code == 401


def test_send_get_completes_with_output_and_author(server):
    flow = make_env("shared", [("echo", "codex", {"prompt": "Return exactly: {prev_output}"})], [])
    flow["share_a2a"] = True
    server.put("/api/environments/shared", flow)
    _, sent = rpc(server, "message/send", {"message": {"messageId": "m1", "role": "user",
        "parts": [{"text": "hello from agent"}], "metadata": {"skillId": "shared"}}})
    task_id = sent["result"]["id"]
    deadline = time.time() + 20
    while time.time() < deadline:
        _, got = rpc(server, "tasks/get", {"id": task_id})
        if got["result"]["status"]["state"] == "completed":
            break
        time.sleep(.1)
    assert got["result"]["status"]["state"] == "completed"
    assert "hello from agent" in got["result"]["artifacts"][0]["parts"][0]["text"]
    assert server.get(f"/api/runs/{task_id}")["author"] == "a2a"
    _, task = rpc(server, "tasks/get", {"id": task_id})
    assert task["result"]["metadata"]["author"] == "a2a"


def test_non_shareable_flow_is_refused(server):
    server.put("/api/environments/private", make_env("private", [("echo", "command", {"cmd": "echo no"})], []))
    _, result = rpc(server, "message/send", {"message": {"messageId": "m2", "role": "user",
        "parts": [{"text": "run"}], "metadata": {"skillId": "private"}}})
    assert result["error"]["code"] == -32004
    assert "not available" in result["error"]["message"].lower()


def test_waiting_and_failed_status_mapping(server):
    from a2a import protocol_status
    assert "input-required" == protocol_status("waiting")
    assert "failed" == protocol_status("failed")


def test_cancel_task(server):
    flow = make_env("waiting", [("approval", "approval", {"prompt": "Continue?"})], [])
    flow["share_a2a"] = True
    server.put("/api/environments/waiting", flow)
    _, sent = rpc(server, "message/send", {"message": {"messageId": "m3", "role": "user",
        "parts": [{"text": "go"}], "metadata": {"skillId": "waiting"}}})
    task_id = sent["result"]["id"]
    _, canceled = rpc(server, "tasks/cancel", {"id": task_id})
    assert canceled["result"]["status"]["state"] == "canceled"


def test_unknown_method_has_method_not_found_code(server):
    _, result = rpc(server, "unknown/method", {})
    assert result["error"]["code"] == -32601
