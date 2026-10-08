"""End-to-end reinstall proof; run alone because it starts real backend processes."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.serial
def test_memory_survives_full_reinstall_from_git(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    proof = backend.parents[1] / "bench" / "memory_reinstall" / "prove.py"
    env = dict(os.environ)
    env["PYTHON"] = sys.executable
    result = subprocess.run(
        [sys.executable, str(proof)],
        cwd=backend.parents[1],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout
    assert "| Overall | PASS |" in result.stdout
