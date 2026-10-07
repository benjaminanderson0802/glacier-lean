"""Acceptance tests for the periodic integration health report."""
from __future__ import annotations

import importlib.util
import json
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
    monkeypatch.setattr(health_check, "upgrade_proposals", lambda: [])
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
    monkeypatch.setattr(health_check, "upgrade_proposals", lambda: [])
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
    sections = health_check.run_health_sections(quick=True)

    security = next(section for section in sections if section["name"] == "security suite")
    assert security["passed"] is False
    assert "not found" in security["summary"].lower()
