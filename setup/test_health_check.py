"""Acceptance tests for the periodic integration health report."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("health_check.py")
spec = importlib.util.spec_from_file_location("health_check", MODULE_PATH)
health_check = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(health_check)


def test_report_shape_and_success_exit(monkeypatch, tmp_path, capsys):
    runners = ["backend", "other suites", "verification benchmark", "security suite"]
    monkeypatch.setattr(health_check, "run_health_sections", lambda quick: [
        {"name": name, "passed": True, "summary": "passed"} for name in runners
    ])
    monkeypatch.setattr(health_check, "check_upgrades", lambda python=None: ([], "Upgrade check complete; proposals only"))
    report_path = tmp_path / "health-report.json"

    code = health_check.main(["--quick", "--report", str(report_path)])

    report = json.loads(report_path.read_text())
    assert code == 0
    assert report["passed"] is True
    assert report["date"]
    assert report["python"]
    assert [section["name"] for section in report["sections"]] == runners
    assert all(set(section) == {"name", "passed", "summary"} for section in report["sections"])
    assert "Health check passed" in capsys.readouterr().out


def test_failed_section_writes_failed_report_and_exits_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(health_check, "run_health_sections", lambda quick: [
        {"name": "backend", "passed": False, "summary": "tests failed"}
    ])
    monkeypatch.setattr(health_check, "check_upgrades", lambda python=None: ([], "Upgrade check complete; proposals only"))
    report_path = tmp_path / "health-report.json"

    code = health_check.main(["--report", str(report_path)])

    assert code == 1
    report = json.loads(report_path.read_text())
    assert report["passed"] is False
    assert report["sections"][0]["passed"] is False
    assert "Health check failed" in capsys.readouterr().out


def test_quick_mode_reuses_current_python(monkeypatch):
    called = []
    monkeypatch.setattr(health_check, "run_commands", lambda specs, python, quick: called.append((python, quick)) or [])
    monkeypatch.setattr(health_check, "run_security_suite", lambda python, results_path: {
        "name": "security suite", "passed": True, "summary": "all attack cases blocked"
    })

    health_check.run_health_sections(quick=True)

    assert called
    assert all(python == health_check.current_python() for python, _ in called)
    assert all(quick is True for _, quick in called)


def test_upgrade_parser_reports_newer_pypi_version_as_proposal():
    output = "Available versions: 2.5.0, 2.4.3, 2.4.0, 1.9.0\n  INSTALLED: 2.4.0\n  LATEST:    2.5.0"

    proposal = health_check.parse_pip_index_versions("sample-package==2.4.0", output)

    assert proposal == {
        "package": "sample-package",
        "installed": "2.4.0",
        "latest": "2.5.0",
        "status": "upgrade available",
        "proposal_only": True,
    }


def test_missing_security_suite_is_reported_as_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(health_check, "REPO", tmp_path)
    monkeypatch.setattr(health_check, "run_commands", lambda specs, python, quick: [])
    sections = health_check.run_health_sections(quick=True)

    security = next(section for section in sections if section["name"] == "security suite")
    assert security["passed"] is False
    assert "not found" in security["summary"].lower()


def test_timeout_is_reported_in_plain_language(monkeypatch):
    monkeypatch.setattr(health_check.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(
        subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 1))))

    sections = health_check.run_commands([("backend", ["{python}", "-m", "pytest"], Path("."))],
                                        Path("python"), quick=True)

    assert sections == [{"name": "backend", "passed": False, "summary": "timed out"}]


def test_upgrade_check_uses_bounded_pip_and_stops_after_network_failure(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, "", "Network is unreachable")

    monkeypatch.setattr(health_check, "pinned_requirements", lambda: ["one==1.0", "two==2.0"])
    monkeypatch.setattr(health_check.subprocess, "run", fake_run)

    proposals, summary = health_check.check_upgrades(Path("python"))

    assert proposals == []
    assert summary == "Upgrade check skipped (no network)"
    assert len(calls) == 1
    assert calls[0][0][-7:] == ["index", "versions", "one", "--timeout", "5", "--retries", "0"]
    assert calls[0][1]["timeout"] <= health_check.UPGRADE_BUDGET_SECONDS


def test_upgrade_check_uses_project_python_for_pip(monkeypatch):
    calls = []
    project_python = Path("/project/.venv/bin/python")
    monkeypatch.setattr(health_check, "pinned_requirements", lambda: ["one==1.0"])

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "Available versions: 1.0\n", "")

    monkeypatch.setattr(health_check.subprocess, "run", fake_run)
    health_check.check_upgrades(project_python)

    assert calls == [[str(project_python), "-m", "pip", "index", "versions", "one",
                      "--timeout", "5", "--retries", "0"]]


def test_default_report_path_is_ignored():
    assert health_check.REPORT == health_check.HERE / ".health" / "health-report.json"
