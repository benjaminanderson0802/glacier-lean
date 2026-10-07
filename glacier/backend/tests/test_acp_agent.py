import os
import shlex
import shutil
import sys

from conftest import env


FAKE_AGENT = os.path.join(os.path.dirname(__file__), "fake_acp_agent.py")


def _python_command(agent):
    return " ".join(shlex.quote(part) for part in (sys.executable, os.path.abspath(agent)))


def _run(server, env_id, workdir, permission_path):
    command = _python_command(FAKE_AGENT)
    server.put(f"/api/environments/{env_id}", env(env_id, [
        ("agent", "acp_agent", {
            "harness": "custom",
            "command": command,
            "workdir": str(workdir),
            "prompt": f"Make a change for {{env}} in run {{run}} after {{prev_output}}. Permission request: {permission_path}",
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
    assert "after . Permission request:" in run["outputs"]["agent"]
    assert run["outputs"]["agent"].endswith("permission=once)")
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


def test_acp_supplies_real_previous_output(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    server.put("/api/environments/acp-prev", env("acp-prev", [
        ("previous", "command", {"cmd": "echo earlier result"}),
        ("agent", "acp_agent", {
            "harness": "custom", "command": _python_command(FAKE_AGENT),
            "workdir": str(workdir),
            "prompt": "Previous result: {prev_output}. Task for {env} in {run}. Permission request: " + str(workdir / "ok.txt"),
            "timeout": 10,
        }),
    ], [("previous", "agent", "")]))
    run = server.wait_run(server.post("/api/environments/acp-prev/run")["run_id"], timeout=15)
    assert run["status"] == "done", run
    assert "Previous result: earlier result" in run["outputs"]["agent"]


def test_acp_denies_shell_request_even_when_command_is_in_workdir(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-shell", workdir, f"shell:{workdir / 'run.sh'}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_denies_move_with_destination_outside_workdir(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-move", workdir, f"move:{workdir / 'a.txt'}:{tmp_path / 'outside.txt'}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_chooses_allow_once_over_allow_always(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-once", workdir, f"both:{workdir / 'inside.txt'}")
    assert run["outputs"]["agent"].endswith("permission=once)")


def test_acp_denies_request_without_paths(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-no-path", workdir, "none:")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_denies_delete_request(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-delete", workdir, f"delete:{workdir / 'file.txt'}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_denies_workdir_itself(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-root", workdir, f"edit:{workdir}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_denies_git_hooks_path(server, tmp_path):
    workdir = tmp_path / "project"
    hook = workdir / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True)
    run = _run(server, "acp-git-hook", workdir, f"edit:{hook}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_denies_symlink_path_resolving_outside_workdir(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workdir / "escape"
    link.symlink_to(outside, target_is_directory=True)
    run = _run(server, "acp-symlink", workdir, f"{link / 'file.txt'}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_checks_nested_new_path_field(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    run = _run(server, "acp-nested", workdir, f"nested:{tmp_path / 'outside.txt'}")
    assert run["outputs"]["agent"].endswith("permission=cancelled)")


def test_acp_catalog_has_expected_fields(server):
    node = next(item for item in server.get("/api/node-types") if item["type"] == "acp_agent")
    assert node["label"] == "Coding agent"
    assert node["worker"] is True
    fields = {field["key"]: field for field in node["fields"]}
    assert fields["harness"]["default"] == "opencode"
    assert fields["harness"]["options"] == ["codex-acp", "opencode", "custom"]
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
    assert "This coding agent isn't installed: opencode" in run["outputs"]["agent"]


def test_acp_missing_package_has_friendly_error(tmp_path, monkeypatch):
    import builtins
    import importlib.util

    path = os.path.join(os.path.dirname(__file__), "..", "nodes", "acp_agent.py")
    spec = importlib.util.spec_from_file_location("acp_agent_without_sdk", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_import = builtins.__import__

    def without_acp(name, *args, **kwargs):
        if name == "acp" or name.startswith("acp."):
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_acp)
    result = module.run({"config": {"harness": "custom", "command": "python fake", "prompt": "hello"},
                         "env_id": "test", "run_id": "run", "home": str(tmp_path)})
    assert result["state"] == "failed"
    assert result["output"] == "Coding agent support is not installed"
