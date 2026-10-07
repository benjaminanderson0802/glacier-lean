#!/usr/bin/env python3
"""Run Glacier's integration health checks and report pinned dependency proposals."""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REQUIREMENTS = HERE / "requirements.txt"
REPORT = REPO / "health-report.json"


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


def upgrade_proposals(python: Path | None = None) -> list[dict]:
    python = python or Path(sys.executable)
    proposals = []
    for requirement in pinned_requirements():
        package = requirement.split("==", 1)[0].strip()
        try:
            result = subprocess.run([str(python), "-m", "pip", "index", "versions", package],
                                    cwd=REPO, text=True, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        proposal = parse_pip_index_versions(requirement, result.stdout + "\n" + result.stderr)
        if proposal:
            proposals.append(proposal)
    return proposals


def command_specs(results_path: Path) -> list[tuple[str, list[str], Path]]:
    py = "{python}"
    return [
        ("backend", [py, "-m", "pytest", "-q", "tests"], REPO / "glacier/backend"),
        ("other suites", [py, "-m", "pytest", "-q", "glacier/importers", "templates", "bench", "tools/scan", "tools/catalog"], REPO),
        ("verification benchmark", [py, "bench/verification/run_glacier.py", "--results", str(results_path)], REPO),
    ]


def run_commands(specs, python: Path, quick: bool) -> list[dict]:
    sections = []
    for name, command, cwd in specs:
        expanded = [str(python) if part == "{python}" else part for part in command]
        try:
            result = subprocess.run(expanded, cwd=cwd, text=True, capture_output=True)
            passed = result.returncode == 0
            details = (result.stdout + "\n" + result.stderr).strip()
            lines = [line.strip() for line in details.splitlines() if line.strip()]
            if name == "verification benchmark":
                rates = [line for line in lines if line.startswith(("False-done rate:", "Verified rate:"))]
                summary = "; ".join(rates) if rates else (lines[-1] if lines else "completed")
            elif not passed:
                failures = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
                summary = failures[-1] if failures else (lines[-1] if lines else "command failed")
            else:
                summary = lines[-1] if lines else "completed"
        except OSError as error:
            passed, summary = False, str(error)
        sections.append({"name": name, "passed": passed, "summary": summary[:500]})
    return sections


def current_python() -> Path:
    project_python = REPO / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return project_python if project_python.is_file() else Path(sys.executable)


def run_health_sections(quick: bool = False) -> list[dict]:
    temporary = None
    run_temporary = tempfile.TemporaryDirectory(prefix="glacier-health-run-")
    run_dir = Path(run_temporary.name)
    prefix_sections = []
    try:
        if quick:
            python = current_python()
        else:
            temporary = tempfile.TemporaryDirectory(prefix="glacier-health-")
            env_dir = Path(temporary.name) / "venv"
            venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
            python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            install = subprocess.run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
                                     cwd=REPO, text=True, capture_output=True)
            install_section = {"name": "fresh environment", "passed": install.returncode == 0,
                               "summary": (install.stderr or install.stdout).strip().splitlines()[-1:][0]
                               if (install.stderr or install.stdout).strip() else "dependencies installed"}
            prefix_sections.append(install_section)
            if install.returncode:
                return prefix_sections
        sections = prefix_sections + run_commands(command_specs(run_dir / "verification-results.md"), python, quick)
        security_dir = REPO / "bench/security"
        if not security_dir.exists():
            sections.append({"name": "security suite", "passed": False,
                             "summary": "Security suite not found at bench/security; no blocked-case result is available."})
        else:
            candidates = [security_dir / "run_glacier.py", security_dir / "test_security.py"]
            runner = next((path for path in candidates if path.is_file()), None)
            if runner is None:
                sections.append({"name": "security suite", "passed": False,
                                 "summary": "Security suite files were not found in bench/security."})
            else:
                if runner.name == "test_security.py":
                    command = [str(python), "-m", "pytest", "-q", str(runner)]
                else:
                    command = [str(python), str(runner)]
                    command += ["--results", str(run_dir / "security-results.md")]
                result = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
                output = (result.stdout + "\n" + result.stderr).strip()
                sections.append({"name": "security suite", "passed": result.returncode == 0,
                                 "summary": next((line.strip() for line in reversed(output.splitlines()) if line.strip()), "completed")[:500]})
        return sections
    finally:
        if temporary is not None:
            temporary.cleanup()
        run_temporary.cleanup()


def print_report(report: dict) -> None:
    print("Health check passed" if report["passed"] else "Health check failed")
    for section in report["sections"]:
        print(f"{'PASS' if section['passed'] else 'FAIL'}  {section['name']}: {section['summary']}")
    if report["proposals"]:
        print("Upgrade proposals (nothing was changed):")
        for item in report["proposals"]:
            print(f"  {item['package']}: {item['installed']} → {item['latest']} (upgrade available)")
    else:
        print("No pinned dependency upgrades found.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="reuse the current Python environment")
    parser.add_argument("--report", type=Path, default=REPORT, help="JSON report path")
    args = parser.parse_args(argv)
    sections = run_health_sections(quick=args.quick)
    proposals = upgrade_proposals()
    report = {"date": date.today().isoformat(), "python": sys.version.split()[0],
              "passed": all(section["passed"] for section in sections),
              "sections": sections, "proposals": proposals}
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
