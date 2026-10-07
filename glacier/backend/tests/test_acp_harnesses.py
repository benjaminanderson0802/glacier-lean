"""Acceptance tests for interchangeable ACP harnesses."""
import os
import sys

from conftest import env


HERE = os.path.dirname(__file__)
FAKE_AGENT = os.path.join(HERE, "fake_acp_agent.py")
FAKE_SECOND = os.path.join(HERE, "fake_acp_agent_second.py")


def _run(server, env_id, agent, workdir, command, harness="custom"):
    server.put(f"/api/environments/{env_id}", env(env_id, [
        ("agent", "acp_agent", {
            "harness": harness,
            "command": command,
            "workdir": str(workdir),
            "prompt": f"create hello.txt containing hi. Permission request: {workdir / 'hello.txt'}",
            "timeout": 10,
        }),
    ], []))
    run = server.wait_run(server.post(f"/api/environments/{env_id}/run")["run_id"], timeout=15)
    return run, workdir / "hello.txt"


def test_two_different_agents_complete_same_goal_and_keep_security(server, tmp_path):
    outcomes = []
    for env_id, agent in (("acp-one", FAKE_AGENT), ("acp-two", FAKE_SECOND)):
        workdir = tmp_path / env_id
        workdir.mkdir()
        command = f'"{sys.executable}" "{agent}"'
        run, target = _run(server, env_id, agent, workdir, command)
        assert run["status"] == "done", run
        assert target.read_text() == "hi"
        outcomes.append(run["outputs"]["agent"])
    assert "permission=once" in outcomes[0]
    assert "permission=once" in outcomes[1]
    assert "execute=cancelled" in outcomes[1]


def test_harness_presets_resolve_documented_commands(monkeypatch, tmp_path):
    import importlib.util
    path = os.path.join(HERE, "..", "nodes", "acp_agent.py")
    spec = importlib.util.spec_from_file_location("acp_agent_presets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/bin/true")
    results = {}
    for harness in ("codex-acp", "opencode"):
        captured = []
        async def fake_run(acp, command, *rest, c=captured):
            c.append(command)
            return "ok", 0
        monkeypatch.setattr(module, "_run_acp", fake_run)
        result = module.run({"config": {"harness": harness, "prompt": "hello"}, "env_id": "x", "run_id": "y", "home": str(tmp_path)})
        assert result["state"] == "done"
        results[harness] = captured[0]
    assert results == {"codex-acp": ["codex-acp"], "opencode": ["opencode", "acp"]}


def test_unknown_harness_uses_plain_missing_agent_message(monkeypatch, tmp_path):
    import importlib.util
    path = os.path.join(HERE, "..", "nodes", "acp_agent.py")
    spec = importlib.util.spec_from_file_location("acp_agent_unknown", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run({"config": {"harness": "made-up", "prompt": "hello"}, "env_id": "x", "run_id": "y", "home": str(tmp_path)})
    assert result["state"] == "failed"
    assert result["output"] == "This coding agent isn't installed: made-up"
