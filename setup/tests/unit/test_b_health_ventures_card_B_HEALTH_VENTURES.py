from __future__ import annotations

from pathlib import Path
import sys
import subprocess

from setup import health_check, venture_health


def test_suite_inventory_includes_each_venture_block_and_installer_directory(tmp_path):
    repo = tmp_path
    for relative in (
        "ventures/tests",
        "ventures/alpha/tests",
        "ventures/blocks/shared/tests",
    ):
        (repo / relative).mkdir(parents=True)

    specs = venture_health.command_specs(repo, Path("python"))

    assert [name for name, _, _ in specs] == [
        "venture suite: ventures/alpha/tests",
        "venture suite: ventures/blocks/shared/tests",
        "venture suite: ventures/tests",
    ]
    assert all(command[-1] == str(repo / name.removeprefix("venture suite: "))
               and cwd == repo for name, command, cwd in specs)


def test_health_specs_append_venture_suites_after_existing_sections(monkeypatch, tmp_path):
    (tmp_path / "ventures" / "alpha" / "tests").mkdir(parents=True)
    monkeypatch.setattr(health_check, "REPO", tmp_path)

    specs = health_check.command_specs(tmp_path / "results.md")

    assert [name for name, _, _ in specs[:3]] == [
        "backend", "other suites", "verification benchmark",
    ]
    assert [name for name, _, _ in specs[3:]] == [
        "venture suite: ventures/alpha/tests",
    ]


def test_colliding_src_and_scripts_imports_run_in_separate_processes(tmp_path):
    repo = tmp_path
    for suite, marker in (("alpha", "alpha"), ("beta", "beta")):
        base = repo / "ventures" / suite
        (base / "tests").mkdir(parents=True)
        for package in ("src", "scripts"):
            (base / package).mkdir()
            (base / package / "__init__.py").write_text("")
            (base / package / "marker.py").write_text(f"VALUE = '{marker}'\n")
        (base / "tests" / "test_colliding_imports.py").write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).parents[1]))\n"
            "from src.marker import VALUE as SRC_VALUE\n"
            "from scripts.marker import VALUE as SCRIPT_VALUE\n"
            f"def test_suite_modules_are_isolated(): assert (SRC_VALUE, SCRIPT_VALUE) == ('{marker}', '{marker}')\n"
        )

    specs = venture_health.command_specs(repo, Path(sys.executable))
    sections = health_check.run_commands(specs, Path(sys.executable), quick=True)

    assert [section["name"] for section in sections] == [
        "venture suite: ventures/alpha/tests",
        "venture suite: ventures/beta/tests",
    ]
    assert all(section["passed"] for section in sections)
    assert all("PASSED:" in section["summary"] for section in sections)


def test_collection_error_is_a_failed_suite():
    passed, summary = venture_health.summarize(
        "venture suite: ventures/alpha/tests", 2,
        "ERROR collecting test_alpha.py\nModuleNotFoundError: missing src package\n",
    )

    assert passed is False
    assert summary.startswith("FAILED:")


def test_skipped_live_canary_is_not_reported_as_live_proof():
    passed, summary = venture_health.summarize(
        "venture suite: ventures/alpha/tests", 0,
        "4 passed, 1 skipped in 0.5s\n"
        "SKIPPED [1] test_live_canary.py:8: opt-in only\n",
    )

    assert passed is True
    assert "live canary skipped" in summary
    assert "no live proof" in summary


def test_all_skipped_suite_is_explicitly_skipped_and_not_passed():
    passed, summary = venture_health.summarize(
        "venture suite: ventures/alpha/tests", 0,
        "1 skipped in 0.1s\nSKIPPED [1] test_live_canary.py:8: opt-in only\n",
    )

    assert passed is False
    assert summary.startswith("SKIPPED:")
    assert "no live proof" in summary


def test_unattempted_suites_are_explicitly_not_run(tmp_path):
    (tmp_path / "ventures" / "alpha" / "tests").mkdir(parents=True)

    sections = venture_health.not_run_sections(tmp_path, "fresh environment setup failed")

    assert sections == [{
        "name": "venture suite: ventures/alpha/tests",
        "passed": False,
        "summary": "NOT RUN: fresh environment setup failed",
    }]


def test_suites_run_in_order_with_a_timeout_and_later_suites_continue(monkeypatch, tmp_path):
    calls = []
    specs = [
        ("venture suite: ventures/alpha/tests", ["python", "-m", "pytest", "alpha"], tmp_path),
        ("venture suite: ventures/beta/tests", ["python", "-m", "pytest", "beta"], tmp_path),
    ]

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[-1] == "alpha":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, "1 passed in 0.01s\n", "")

    monkeypatch.setattr(health_check, "command_timeout", lambda: 7)
    monkeypatch.setattr(health_check.subprocess, "run", fake_run)

    sections = health_check.run_commands(specs, Path("python"), quick=True)

    assert [command[-1] for command, _ in calls] == ["alpha", "beta"]
    assert all(kwargs["timeout"] == 7 for _, kwargs in calls)
    assert [section["passed"] for section in sections] == [False, True]
    assert sections[0]["summary"] == "FAILED: timed out"
    assert sections[1]["summary"] == "PASSED: 1 passed in 0.01s"
