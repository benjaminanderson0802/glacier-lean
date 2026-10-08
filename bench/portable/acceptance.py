"""Independent checks for the portable backend live bench."""

from pathlib import Path
import subprocess


def verify_python_function(workdir: Path, python: str = "python") -> tuple[bool, str]:
    test = subprocess.run(
        [python, "-m", "pytest", "-q"], cwd=workdir,
        capture_output=True, text=True, timeout=90,
    )
    return test.returncode == 0, (test.stdout + test.stderr).strip()[-2000:]


def verify_hello_file(workdir: Path) -> tuple[bool, str]:
    path = workdir / "hello.txt"
    passed = path.is_file() and path.read_text(encoding="utf-8") == "hello from glacier"
    return passed, "hello.txt exact content check"
