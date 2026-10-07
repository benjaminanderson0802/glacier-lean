#!/usr/bin/env python3
"""Run Glacier's integration health checks and report pinned dependency proposals."""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import venv

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REQUIREMENTS = HERE / "requirements.txt"
REPORT = HERE / ".health" / "health-report.json"
DEFAULT_TIMEOUT_SECONDS = 30 * 60
UPGRADE_BUDGET_SECONDS = 90
NETWORK_FAILURE_HINTS = ("network is unreachable", "temporary failure in name resolution", "could not resolve",
                         "connection timed out", "connection refused", "no route to host", "proxyerror",
                         "failed to establish a new connection", "name or service not known")


def parse_pip_index_versions(requirement: str, output: str) -> dict | None:
    """Turn pip's index output into an upgrade proposal; never mutate requirements."""
    match = re.match(r"\s*([A-Za-z0-9_.-]+)==([^\s;]+)", requirement)
    if not match:
        return None
    package, installed = match.groups()
    latest_match = re.search(r"^\s*LATEST:\s*([^\s]+)", output, re.MULTILINE | re.IGNORECASE)
    if latest_match:
        latest = latest_match.group(1)
    else:
        available = re.search(r"Available versions:\s*([^\n]+)", output, re.IGNORECASE)
        if not available:
            return None
        versions = [value.strip() for value in available.group(1).split(",") if value.strip()]
        latest = versions[0] if versions else ""
    if not latest or latest == installed:
        return None
    return {"package": package, "installed": installed, "latest": latest,
            "status": "upgrade available", "proposal_only": True}


def pinned_requirements() -> list[str]:
    return [line.strip() for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "==" in line]


def check_upgrades(python: Path | None = None) -> tuple[list[dict], str]:
    """Check pins within one wall-clock budget; networking failures stop further requests."""
    python = python or Path(sys.executable)
    proposals: list[dict] = []
    deadline = time.monotonic() + UPGRADE_BUDGET_SECONDS
    pip_executable = shutil.which("pip")
    for requirement in pinned_requirements():
        package = requirement.split("==", 1)[0].strip()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return proposals, "Upgrade check stopped at its 90-second time limit"
        command = ([pip_executable, "index", "versions", package, "--timeout", "5", "--retries", "0"]
                   if pip_executable else
                   [str(python), "-m", "pip", "index", "versions", package,
                    "--timeout", "5", "--retries", "0"])
        try:
            result = subprocess.run(command, cwd=REPO, text=True, capture_output=True,
                                    timeout=min(remaining, 10))
        except subprocess.TimeoutExpired:
            return proposals, "Upgrade check skipped (no network)"
        except OSError:
            return proposals, "Upgrade check skipped (no network)"
        output = result.stdout + "\n" + result.stderr
        if result.returncode and any(hint in output.lower() for hint in NETWORK_FAILURE_HINTS):
            return proposals, "Upgrade check skipped (no network)"
        if result.returncode:
            return proposals, f"Upgrade check stopped: pip could not check {package}"
        proposal = parse_pip_index_versions(requirement, output)
        if proposal:
            proposals.append(proposal)
    return proposals, "Upgrade check complete; proposals only"


def command_specs(results_path: Path) -> list[tuple[str, list[str], Path]]:
    py = "{python}"
    return [
        ("backend", [py, "-m", "pytest", "-q", "tests"], REPO / "glacier/backend"),
        ("other suites", [py, "-m", "pytest", "-q", "glacier/importers", "templates", "bench", "tools/scan", "tools/catalog"], REPO),
        ("verification benchmark", [py, "bench/verification/run_glacier.py", "--results", str(results_path)], REPO),
    ]


def command_timeout() -> int:
    try:
        return max(1, int(os.environ.get("GLACIER_HEALTH_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def result_summary(name: str, passed: bool, output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if name == "verification benchmark":
        rates = [line for line in lines if line.startswith(("False-done rate:", "Verified rate:"))]
        return "; ".join(rates) if rates else (lines[-1] if lines else "completed")
    if not passed:
        failures = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
        return failures[-1] if failures else (lines[-1] if lines else "command failed")
    return lines[-1] if lines else "completed"


def run_commands(specs, python: Path, quick: bool) -> list[dict]:
    sections = []
    for name, command, cwd in specs:
        expanded = [str(python) if part == "{python}" else part for part in command]
        try:
            result = subprocess.run(expanded, cwd=cwd, text=True, capture_output=True,
                                    timeout=command_timeout())
            passed = result.returncode == 0
            summary = result_summary(name, passed, result.stdout + "\n" + result.stderr)[:500]
        except subprocess.TimeoutExpired:
            passed, summary = False, "timed out"
        except OSError as error:
            passed, summary = False, str(error)[:500]
        sections.append({"name": name, "passed": passed, "summary": summary})
    return sections


def current_python() -> Path:
    project_python = REPO / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return project_python if project_python.is_file() else Path(sys.executable)


def run_security_suite(python: Path, results_path: Path) -> dict:
    security_dir = REPO / "bench/security"
    if not security_dir.exists():
        return {"name": "security suite", "passed": False,
                "summary": "Security suite not found at bench/security; no blocked-case result is available."}
    runner = security_dir / "run_glacier.py"
    tests = security_dir / "test_runner.py"
    if runner.is_file():
        command = [str(python), str(runner), "--results", str(results_path)]
    elif tests.is_file():
        command = [str(python), "-m", "pytest", "-q", str(security_dir)]
    else:
        return {"name": "security suite", "passed": False,
                "summary": "Security suite files were not found in bench/security."}
    try:
        result = subprocess.run(command, cwd=REPO, text=True, capture_output=True,
                                timeout=command_timeout())
    except subprocess.TimeoutExpired:
        return {"name": "security suite", "passed": False, "summary": "timed out"}
    except OSError as error:
        return {"name": "security suite", "passed": False, "summary": str(error)[:500]}
    output = result.stdout + "\n" + result.stderr
    return {"name": "security suite", "passed": result.returncode == 0,
            "summary": result_summary("security suite", result.returncode == 0, output)[:500]}


def run_health_sections(quick: bool = False) -> list[dict]:
    temporary = None
    run_temporary = tempfile.TemporaryDirectory(prefix="glacier-health-run-")
    run_dir = Path(run_temporary.name)
    try:
        if quick:
            python = current_python()
            prefix_sections = []
        else:
            temporary = tempfile.TemporaryDirectory(prefix="glacier-health-")
            env_dir = Path(temporary.name) / "venv"
            venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
            python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            try:
                install = subprocess.run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
                                         cwd=REPO, text=True, capture_output=True, timeout=command_timeout())
                install_section = {"name": "fresh environment", "passed": install.returncode == 0,
                                   "summary": result_summary("fresh environment", install.returncode == 0,
                                                             install.stdout + "\n" + install.stderr)[:500]}
            except subprocess.TimeoutExpired:
                install_section = {"name": "fresh environment", "passed": False, "summary": "timed out"}
            except OSError as error:
                install_section = {"name": "fresh environment", "passed": False, "summary": str(error)[:500]}
            prefix_sections = [install_section]
            if not install_section["passed"]:
                return prefix_sections
        sections = prefix_sections + run_commands(command_specs(run_dir / "verification-results.md"), python, quick)
        sections.append(run_security_suite(python, run_dir / "security-results.md"))
        return sections
    finally:
        if temporary is not None:
            temporary.cleanup()
        run_temporary.cleanup()


def print_report(report: dict) -> None:
    print("Health check passed" if report["passed"] else "Health check failed")
    for section in report["sections"]:
        print(f"{'PASS' if section['passed'] else 'FAIL'}  {section['name']}: {section['summary']}")
    print(report["upgrade_summary"])
    if report["proposals"]:
        print("Upgrade proposals (nothing was changed):")
        for item in report["proposals"]:
            print(f"  {item['package']}: {item['installed']} → {item['latest']} (upgrade available)")
    else:
        print("No pinned dependency upgrades found.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="reuse the current Python environment")
    parser.add_argument("--report", type=Path, help="JSON report path (defaults to setup/.health/health-report.json)")
    args = parser.parse_args(argv)
    sections = run_health_sections(quick=args.quick)
    proposals, upgrade_summary = check_upgrades(current_python())
    report = {"date": date.today().isoformat(), "python": sys.version.split()[0],
              "passed": all(section["passed"] for section in sections),
              "sections": sections, "proposals": proposals, "upgrade_summary": upgrade_summary}
    report_path = args.report or REPORT
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
