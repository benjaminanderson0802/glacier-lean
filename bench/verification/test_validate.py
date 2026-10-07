"""Acceptance test for the verification benchmark validator."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


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
