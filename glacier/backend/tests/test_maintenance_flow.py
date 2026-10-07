"""Offline acceptance checks for the weekly maintenance proposal flow."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "setup" / "selfbuild"))

import maintenance
sys.path.insert(0, str(ROOT / "tools" / "scan"))
import scan


def test_parse_pip_outdated_fixture():
    rows = maintenance.parse_pip_outdated(
        "Package Version Latest Type\nrequests 2.31.0 3.0.0 wheel\nflask 2.3.0 2.3.0 wheel\n"
    )
    assert rows == [{"name": "requests", "current": "2.31.0", "latest": "3.0.0", "source": "python"}]


def test_parse_npm_outdated_fixture():
    rows = maintenance.parse_npm_outdated(
        '{"left-pad":{"current":"1.3.0","wanted":"1.3.0","latest":"2.0.0","type":"dependencies"}}',
        "web",
    )
    assert rows == [{"name": "left-pad", "current": "1.3.0", "latest": "2.0.0", "source": "npm:web"}]


def test_license_filter_keeps_osi_and_drops_proprietary():
    rows = [
        {"name": "good", "current": "1.0", "latest": "2.0", "source": "npm:web", "license": "MIT"},
        {"name": "closed", "current": "1.0", "latest": "2.0", "source": "python", "license": "Commercial License"},
    ]
    proposed, rejected = maintenance.filter_licenses(rows)
    assert [row["name"] for row in proposed] == ["good"]
    assert [row["name"] for row in rejected] == ["closed"]


def test_note_rendering_is_plain_language_and_has_test_board():
    note = maintenance.render_note(
        "run-123", "2026-10-07",
        [{"name": "alpha", "current": "1.0", "latest": "2.0", "source": "python", "license": "MIT", "care": True}],
        [],
        [{"name": "backend", "passed": True, "summary": "12 passed", "slowest": ["test_slow (3.2s)"]},
         {"name": "screen", "passed": False, "summary": "1 failed", "slowest": []}],
    )
    assert "alpha: 1.0 → 2.0" in note and "needs care" in note
    assert "12 passed" in note and "1 failed" in note and "test_slow" in note
    assert "owner" in note.lower()


def test_flow_is_weekly_proposal_only_without_worker_or_push():
    flow = json.loads((ROOT / "flows/self/maintenance.json").read_text(encoding="utf-8"))
    raw = json.dumps(flow).lower()
    assert any(node["type"] == "schedule" and node["config"].get("cron") == "0 9 * * 1" for node in flow["nodes"])
    assert all(node["type"] != "codex" for node in flow["nodes"])
    assert "git push" not in raw and "workspace-write" not in raw
    assert any(node["id"] == "status_note" and node["type"] == "note" for node in flow["nodes"])
    assert "proposal" in raw and "results" in raw
    command = next(node["config"]["cmd"] for node in flow["nodes"] if node["id"] == "maintenance")
    assert "maintenance.py" in command and "--repo" in command and "{repo}" in command and "{run}" in command
    assert all(node["config"].get("cwd") == "{repo}" for node in flow["nodes"] if node["type"] == "command")
    assert flow["nodes"][-1]["config"]["path"] == "proposals/maintenance-{date}.md"


def test_fake_run_renders_exactly_one_proposal_note(tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance.tool_scan, "discover_records", lambda **kwargs: ([], []))
    calls = []
    (tmp_path / "setup").mkdir()
    (tmp_path / "setup" / "requirements.txt").write_text("alpha==1.0\n", encoding="utf-8")

    def command_runner(command, cwd, timeout):
        calls.append((command, cwd))
        if command[:2] == ["fake-python", "-m"] and "pip" in command:
            if "show" in command:
                return maintenance.CommandResult(0, "Name: alpha\nLicense: MIT\n", "")
            return maintenance.CommandResult(0, "Package Version Latest Type\nalpha 1.0 2.0 wheel\n", "")
        if command[:2] in (["fake-npm", "outdated"], ["fake-npm", "view"]):
            return maintenance.CommandResult(0, "{}", "")
        if command[:2] == ["fake-test"]:
            return maintenance.CommandResult(0, "2 passed in 1.0s\n", "")
        if command[:2] == ["fake-ui"]:
            return maintenance.CommandResult(0, "UI check passed\n", "")
        raise AssertionError(command)

    config = maintenance.RunConfig(
        repo=tmp_path, run_id="run-fake", date="2026-10-07",
        python_command=["fake-python"], npm_command=["fake-npm"],
        backend_command=["fake-test"], ui_command=["fake-ui"], timeout=1800,
    )
    result = maintenance.run_maintenance(config, command_runner=command_runner)
    flow = json.loads((ROOT / "flows/self/maintenance.json").read_text(encoding="utf-8"))
    assert result["path"] == "proposals/maintenance-2026-10-07.md"
    assert result["author"] == "run:run-fake"
    assert "2 passed" in result["body"] and "alpha: 1.0 → 2.0" in result["body"]
    assert sum(node["type"] == "note" for node in flow["nodes"]) == 1
    assert len(calls) == 4


def test_proposal_note_directly_follows_the_maintenance_step_and_saves_its_output():
    flow = json.loads((ROOT / "flows/self/maintenance.json").read_text(encoding="utf-8"))
    note = next(node for node in flow["nodes"] if node["id"] == "status_note")
    assert {"source": "maintenance", "target": "status_note"}.items() <= next(
        e for e in flow["edges"] if e["target"] == "status_note").items()
    assert "{prev_output}" in note["config"]["template"]


def test_tool_discovery_section_uses_scanner_records_and_shows_proposal_fields():
    record = scan.Tool("helpful-tool", "MIT", "https://example.test/tool", maintenance.date_type(2026, 10, 7),
                       "Helps connect local models to files.", source="mcp")
    section = maintenance.render_tool_section([record])
    assert "## New tools worth a look" in section
    assert "helpful-tool" in section and "https://example.test/tool" in section
    assert "MIT" in section and "2026-10-07" in section
    assert "Helps connect local models to files." in section
    assert section.rstrip().endswith("Nothing was installed. To try one, approve it and a feature run will add it with tests.")


def test_tool_discovery_handles_source_failure_and_caps_whole_note(monkeypatch, tmp_path):
    today = maintenance.date_type(2026, 10, 7)
    records = [scan.Tool(f"tool-{index}", "MIT", f"https://example.test/{index}/" + "x" * 900, today,
                         "Useful helper " + "x" * 400, source="mcp") for index in range(10)]
    monkeypatch.setattr(maintenance.tool_scan, "discover_records", lambda **kwargs: (records, ["MCP registry"]))
    def command_runner(command, cwd, timeout):
        if command[:2] == ["fake-python", "-m"] and "pip" in command:
            return maintenance.CommandResult(0, "Package Version Latest Type\n", "")
        if command[:2] in (["fake-npm", "outdated"], ["fake-npm", "view"]):
            return maintenance.CommandResult(0, "{}", "")
        if command == ["fake-test"]:
            return maintenance.CommandResult(0, "2 passed\n", "")
        if command == ["fake-ui"]:
            return maintenance.CommandResult(0, "UI check passed\n", "")
        raise AssertionError(command)

    config = maintenance.RunConfig(tmp_path, "run-cap", "2026-10-07", ["fake-python"], ["fake-npm"],
                                   ["fake-test"], ["fake-ui"], 1800)
    note = maintenance.run_maintenance(config, command_runner=command_runner)["body"]
    assert "MCP registry: could not check right now" in note
    assert len(note) <= 7500
    assert "more not shown)" in note
    assert note.rstrip().endswith("Nothing was installed. To try one, approve it and a feature run will add it with tests.")


def test_length_cap_trims_tool_entries_before_package_entries():
    today = maintenance.date_type(2026, 10, 7)
    tools = [scan.Tool(f"tool-{index}", "MIT", f"https://example.test/{index}/" + "x" * 1100,
                       today, "Useful", source="mcp") for index in range(10)]
    packages = [{"name": f"package-{index}-" + "p" * 1100, "current": "1.0", "latest": "2.0",
                 "source": "python", "license": "MIT", "care": False} for index in range(10)]
    note = maintenance.render_note("run-cap", "2026-10-07", packages, [], [], tools)
    assert len(note) <= 7500
    assert "more not shown)" in note
    assert "package-0-" in note and "package-9-" not in note
    assert "tool-0" not in note


def test_proposal_note_directly_follows_the_maintenance_step_and_saves_its_output():
    flow = json.loads((ROOT / "flows/self/maintenance.json").read_text(encoding="utf-8"))
    note = next(node for node in flow["nodes"] if node["id"] == "status_note")
    incoming = [e["source"] for e in flow["edges"] if e["target"] == "status_note"]
    assert incoming == ["maintenance"]
    assert "{prev_output}" in note["config"]["template"]
