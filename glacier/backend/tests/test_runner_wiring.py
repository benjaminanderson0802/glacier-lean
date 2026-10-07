import socket
import time

import runner
import sandboxing
import store
from conftest import env, FAKE_CODEX


def _node(run_id, config):
    return {"id": "cmd", "type": "command", "config": config}


def test_sandboxed_command_cannot_write_outside_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    monkeypatch.delenv("GLACIER_SANDBOX", raising=False)
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    result = runner.run_node("flow", "run1", _node("run1", {
        "cmd": f"echo inside > inside.txt; echo outside > {outside}", "sandbox": "on"
    }), None, str(workspace))
    assert (workspace / "inside.txt").read_text().strip() == "inside"
    assert not outside.exists()
    assert result["state"] == "failed"  # outside redirection is denied by the kernel


def test_sandboxed_command_cannot_reach_local_tcp_server(tmp_path, monkeypatch):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    monkeypatch.delenv("GLACIER_SANDBOX", raising=False)
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    result = runner.run_node("flow", "run2", _node("run2", {
            "cmd": f"/usr/bin/python3 -c 'import socket; s=socket.socket(); s.settimeout(1); s.connect((\"127.0.0.1\", {port}))'",
            "sandbox": "on"
        }), None, str(tmp_path))
    listener.close()
    assert result["state"] == "failed"


def test_flow_and_environment_can_enable_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    seen = []
    monkeypatch.setattr(sandboxing, "wrap", lambda command, workdir, hosts: seen.append((command, hosts)) or ["/bin/true"])
    monkeypatch.setenv("GLACIER_SANDBOX", "on")
    result = runner.run_node("flow", "run-flow", _node("run-flow", {"cmd": "true"}), None, str(tmp_path))
    assert result["state"] == "done"
    assert seen == [("true", [])]


def test_network_allow_requests_supported_hostless_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    monkeypatch.setattr(sandboxing, "wrap", lambda *args: (_ for _ in ()).throw(
        NotImplementedError("allowed-host networking needs an allowlisting proxy; direct network stays blocked")))
    monkeypatch.delenv("GLACIER_SANDBOX", raising=False)
    result = runner.run_node("flow", "run-network", _node("run-network", {
        "cmd": "true", "sandbox": "on", "network": "allow"
    }), None, str(tmp_path))
    assert result["state"] == "failed"
    assert "allowlisting proxy" in result["output"]


def test_unavailable_sandbox_fails_with_plain_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(sandboxing, "wrap", lambda *args: (_ for _ in ()).throw(RuntimeError("OS sandbox unavailable: sandbox is unavailable here")))
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    result = runner.run_node("flow", "run3", _node("run3", {"cmd": "echo must-not-run", "sandbox": "on"}), None, str(tmp_path))
    assert result["state"] == "failed"
    assert result["output"] == "OS sandbox unavailable: sandbox is unavailable here"


def test_codex_setting_is_default_and_explicit_readonly_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_CODEX_SANDBOX", "workspace-write")
    monkeypatch.setattr(runner, "CODEX_BIN", FAKE_CODEX, raising=False)
    monkeypatch.setattr(store, "set_node", lambda *args, **kwargs: None)
    seen = {}
    popen = runner.subprocess.Popen
    def capture(args, *pargs, **kwargs):
        seen["sandbox"] = args[args.index("-s") + 1]
        return popen(args, *pargs, **kwargs)
    monkeypatch.setattr(runner.subprocess, "Popen", capture)
    result = runner.run_codex("flow", "run4", "cx", {"prompt": "say hi", "sandbox": "read-only"}, "", ws=str(tmp_path))
    assert seen["sandbox"] == "read-only"


def test_run_queue_waits_at_effective_limit(server, monkeypatch):
    monkeypatch.setenv("GLACIER_MAX_PARALLEL_RUNS", "1")
    server.put("/api/environments/limited", env("limited", [
        ("wait", "command", {"cmd": "sleep 1; echo finished"})
    ], []))
    first_id = server.post("/api/environments/limited/run")["run_id"]
    deadline = time.time() + 10
    while time.time() < deadline:
        first = server.get(f"/api/runs/{first_id}")
        if first["status"] == "running":
            break
        time.sleep(0.05)
    second_id = server.post("/api/environments/limited/run")["run_id"]
    deadline = time.time() + 3
    while time.time() < deadline:
        second = server.get(f"/api/runs/{second_id}")
        if second["status"] == "queued":
            break
        time.sleep(0.05)
    assert second["status"] == "queued"
    assert second["waiting_on"] == "Waiting for another run to finish"
    assert server.wait_run(first_id)["status"] == "done"
    assert server.wait_run(second_id, timeout=10)["status"] == "done"
