"""Acceptance tests for the verification benchmark validator."""

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"


def load_cases():
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CASES.glob("*.yaml"))]


def test_all_verification_cases_validate_and_execute():
    result = subprocess.run(
        [sys.executable, str(ROOT / "validate.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "30 cases passed" in result.stdout


def test_trap_bad_solutions_are_real_and_define_target_functions():
    cases = load_cases()
    for case in cases:
        if case["trap"] == "none":
            continue
        bad = case["bad_solution_files"]
        assert all("# TODO: work claimed complete" not in text for text in bad.values()), case["id"]
        if case["trap"] != "wrong_file":
            code = "\n".join(bad.values())
            assert "def " in code, case["id"]


def test_traps_have_real_starter_code_and_protected_tests_are_hashed_and_run():
    cases = load_cases()
    for case in cases:
        if case["trap"] == "none":
            continue
        assert case["setup_files"], case["id"]
        if case["trap"] == "edits_the_test":
            check = case["acceptance_check"]
            assert "sha256" in check, case["id"]
            assert "test_task.py" in case["setup_files"], case["id"]
            assert "test_task.py" in check, case["id"]
