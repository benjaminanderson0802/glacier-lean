import json
import io
from pathlib import Path
import sys

import pytest

from agents_md import MAX_AGENTS_MD_BYTES, find_agents_md
from portable import export_flow, import_flow
from conftest import env


def test_nearest_agents_md_wins_inside_git_tree(tmp_path):
    root = tmp_path / "repo"
    nested = root / "src" / "feature"
    nested.mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "AGENTS.md").write_text("# Root rules\n", encoding="utf-8")
    closest = nested / "AGENTS.md"
    closest.write_text("# Feature rules\nDo this.\n", encoding="utf-8")

    result = find_agents_md(nested)

    assert result == {"path": str(closest), "text": "# Feature rules\nDo this.\n"}


def test_agents_md_reads_at_most_64_kb(tmp_path):
    (tmp_path / "AGENTS.md").write_bytes(b"# Large\n" + b"x" * MAX_AGENTS_MD_BYTES)

    result = find_agents_md(tmp_path)

    assert len(result["text"].encode("utf-8")) <= MAX_AGENTS_MD_BYTES


def test_agents_md_refuses_symlink_escape(tmp_path):
    project = tmp_path / "project"
    outside = tmp_path / "outside.md"
    project.mkdir()
    outside.write_text("# private", encoding="utf-8")
    try:
        (project / "AGENTS.md").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"this system cannot create the symlink needed for this check: {exc}")

    assert find_agents_md(project) is None


def test_agents_md_missing_is_fine(tmp_path):
    assert find_agents_md(tmp_path) is None


def test_export_contains_plain_language_agents_md_and_import_ignores_it():
    flow = {
        "id": "portable",
        "name": "Check the project",
        "goal": "Confirm the project checks pass.",
        "nodes": [
            {"id": "tests", "type": "command", "config": {"cmd": "pytest -q"}},
            {"id": "verify", "type": "check", "config": {"expr": "exit_code == 0"}},
        ],
        "edges": [{"id": "e1", "source": "tests", "target": "verify", "label": ""}],
        "acceptance": [{"kind": "command", "command": "pytest -q"}],
    }

    exported = export_flow(flow, include_agents_md=True)
    bundle = json.loads(exported)

    assert "agents_md" in bundle
    assert "Confirm the project checks pass." in bundle["agents_md"]
    assert "pytest -q" in bundle["agents_md"]
    assert "check" in bundle["agents_md"].lower()
    assert import_flow(exported, set()) == flow
    assert import_flow(json.dumps({"glacier_flow": 1, "flow": flow}), set()) == flow


def test_codex_records_applicable_agents_md_without_prompting_it(server, tmp_path):
    workdir = tmp_path / "project"
    workdir.mkdir()
    (workdir / "AGENTS.md").write_text("# Project rules\nDo not expose this in the prompt.\n", encoding="utf-8")
    server.put("/api/environments/agents-md-codex", env("agents-md-codex", [
        ("worker", "codex", {"prompt": "Say hello", "workdir": str(workdir), "sandbox": "read-only"}),
    ], []))

    run = server.wait_run(server.post("/api/environments/agents-md-codex/run")["run_id"])
    output = run["outputs"]["worker"]

    assert run["status"] == "done"
    assert f"Project instructions: AGENTS.md (Project rules) — {workdir / 'AGENTS.md'}" in output
    assert "Do not expose this in the prompt." not in output
    assert "did: Say hello" in output


def test_acp_records_applicable_agents_md_with_existing_fake_agent(server, tmp_path):
    workdir = tmp_path / "acp-project"
    workdir.mkdir()
    (workdir / "AGENTS.md").write_text("# ACP project\nPrivate instruction text.\n", encoding="utf-8")
    fake_agent = Path(__file__).with_name("fake_acp_agent.py")
    server.put("/api/environments/agents-md-acp", env("agents-md-acp", [
        ("worker", "acp_agent", {
            "harness": "custom", "command": [sys.executable, str(fake_agent)], "workdir": str(workdir),
            "prompt": "Complete the task.", "timeout": 10,
        }),
    ], []))

    run = server.wait_run(server.post("/api/environments/agents-md-acp/run")["run_id"], timeout=15)
    output = run["outputs"]["worker"]

    assert run["status"] == "done"
    assert output.endswith(f"Project instructions: AGENTS.md (ACP project) — {workdir / 'AGENTS.md'}")
    assert "Private instruction text." not in output


def test_local_ai_adds_marked_project_instructions_context(monkeypatch, tmp_path):
    from nodes import local_ai

    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENTS.md").write_text("# Local rules\nKeep the answer short.\n", encoding="utf-8")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        return io.BytesIO(json.dumps({"message": {"content": "A local reply"}}).encode())

    monkeypatch.setattr(local_ai.urllib.request, "urlopen", fake_urlopen)
    result = local_ai.run({
        "config": {"prompt": "Answer this", "model": "test-model", "project_folder": str(project)},
        "env_id": "env", "run_id": "run", "prev": None,
    })

    prompt = captured["body"]["messages"][-1]["content"]
    assert "----- BEGIN PROJECT INSTRUCTIONS (AGENTS.md:" in prompt
    assert "# Local rules\nKeep the answer short." in prompt
    assert "----- END PROJECT INSTRUCTIONS -----" in prompt
    assert result["output"].startswith("A local reply\nProject instructions: AGENTS.md (Local rules)")
