import os
import shutil
import sys

from conftest import env


FAKE_AGENT = os.path.join(os.path.dirname(__file__), "fake_acp_agent.py")


def _run(server, env_id, workdir, permission_path):
    command = f'"{sys.executable}" "{FAKE_AGENT}"'
    server.put(f"/api/environments/{env_id}", env(env_id, [
        ("agent", "acp_agent", {
            "harness": "custom",
            "command": command,
            "workdir": str(workdir),
            "prompt": f"Make a change for {{env}} in run {{run}} after {{prev_output}}. Permission path: {permission_path}",
            "timeout": 10,
        }),
    ], []))
    run_id = server.post(f"/api/environments/{env_id}/run")["run_id"]
    return server.wait_run(run_id, timeout=15)


def test_acp_custom_agent_prompt_permission_and_usage(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-in", workdir, workdir / "inside.txt")

    assert run["status"] == "done", run
    assert run["outputs"]["agent"].startswith("done: Make a change for acp-in in run ")
    assert "after . Permission path:" in run["outputs"]["agent"]
    assert run["outputs"]["agent"].endswith("permission=selected)")
    assert run["usage"]["agent"] == {
        "model": "custom", "route": "acp/custom", "tokens_in": 0,
        "tokens_out": 0, "cost_usd": 0.0,
    }


def test_acp_denies_permission_outside_workdir(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-out", workdir, tmp_path / "outside.txt")

    assert run["status"] == "done", run
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_catalog_has_expected_fields(server):
    node = next(item for item in server.get("/api/node-types") if item["type"] == "acp_agent")
    assert node["label"] == "Coding agent"
    assert node["worker"] is True
    fields = {field["key"]: field for field in node["fields"]}
    assert fields["harness"]["default"] == "opencode"
    assert fields["harness"]["options"] == ["opencode", "gemini", "custom"]
    assert fields["timeout"]["default"] == 1800


def test_acp_missing_harness_binary_has_friendly_error(make_server, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("GIT_PYTHON_GIT_EXECUTABLE", shutil.which("git") or "/usr/bin/git")
    server = make_server().start()
    server.put("/api/environments/acp-missing", env("acp-missing", [
        ("agent", "acp_agent", {"harness": "opencode", "prompt": "Say hello"}),
    ], []))
    run = server.wait_run(server.post("/api/environments/acp-missing/run")["run_id"])

    assert run["status"] == "failed", run
    assert "OpenCode is not installed" in run["outputs"]["agent"]
