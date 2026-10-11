"""Discover and describe isolated venture and shared-block pytest suites."""
from __future__ import annotations

from pathlib import Path
import re


def test_directories(repo: Path) -> list[Path]:
    """Return venture and block test directories in stable, disjoint order."""
    ventures = repo / "ventures"
    if not ventures.is_dir():
        return []
    found = [path for path in ventures.glob("*/tests") if path.is_dir()]
    installer_suite = ventures / "tests"
    if installer_suite.is_dir():
        found.append(installer_suite)
    blocks = ventures / "blocks"
    if blocks.is_dir():
        found.extend(path for path in blocks.glob("*/tests") if path.is_dir())
    return sorted(set(found), key=lambda path: path.relative_to(repo).as_posix())


def suite_name(repo: Path, test_dir: Path) -> str:
    return f"venture suite: {test_dir.relative_to(repo).as_posix()}"


def summarize(name: str, returncode: int, output: str) -> tuple[bool, str]:
    """Summarize pytest without calling an empty or skipped suite live proof."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if returncode == 5 or any("no tests ran" in line.lower() for line in lines):
        return False, "SKIPPED: no tests collected; no proof available"

    summary_lines = [line for line in lines if re.search(
        r"\b\d+\s+(?:passed|failed|error|errors|skipped|xfailed|xpassed)\b", line, re.I
    )]
    counts = summary_lines[-1] if summary_lines else (lines[-1] if lines else "no pytest output")
    failures = returncode != 0 or any(line.startswith(("FAILED ", "ERROR ")) for line in lines)
    if failures:
        detail = next((line for line in reversed(lines)
                       if line.startswith(("FAILED ", "ERROR "))), counts)
        return False, f"FAILED: {detail}"

    skipped_live_canary = any(
        "skip" in line.lower() and "canary" in line.lower()
        for line in lines
    )
    has_passed = any(re.search(r"\b\d+\s+passed\b", line, re.I) for line in summary_lines)
    has_skip = any(re.search(r"\b\d+\s+skipped\b", line, re.I) for line in summary_lines)
    if not has_passed and has_skip:
        return False, f"SKIPPED: {counts}; no live proof"
    if skipped_live_canary:
        return True, f"PASSED: {counts}; live canary skipped, no live proof"
    return True, f"PASSED: {counts}"


def command_specs(repo: Path, python: Path) -> list[tuple[str, list[str], Path]]:
    """Create one pytest process per suite to isolate generic src/scripts imports."""
    return [
        (suite_name(repo, test_dir),
         [str(python), "-m", "pytest", "-q", "-ra", str(test_dir)], repo)
        for test_dir in test_directories(repo)
    ]


def not_run_sections(repo: Path, reason: str) -> list[dict]:
    return [{"name": suite_name(repo, test_dir), "passed": False,
             "summary": f"NOT RUN: {reason}"}
            for test_dir in test_directories(repo)]
