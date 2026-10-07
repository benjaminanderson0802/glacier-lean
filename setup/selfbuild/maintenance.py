#!/usr/bin/env python3
"""Collect dependency and test-board facts for the weekly maintenance proposal."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date as date_type
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
OSI_LICENSES = {
    "0bsd", "afl-3.0", "agpl-3.0", "apache-2.0", "artistic-2.0", "bsd-2-clause",
    "bsd-3-clause", "bsl-1.0", "cddl-1.0", "ecl-2.0", "epl-1.0", "epl-2.0",
    "eupl-1.1", "eupl-1.2", "gpl-2.0", "gpl-3.0", "isc", "lgpl-2.1", "lgpl-3.0",
    "mit", "mpl-2.0", "ms-pl", "osl-3.0", "postgresql", "python-2.0", "unlicense",
    "upl-1.0", "wtfpl", "zlib",
}


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class RunConfig:
    repo: Path
    run_id: str
    date: str
    python_command: list[str]
    npm_command: list[str]
    backend_command: list[str]
    ui_command: list[str]
    timeout: int = 1800


def parse_pip_outdated(output: str) -> list[dict]:
    """Parse pip list --outdated --format=columns output."""
    rows = []
    for line in output.splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s+([^\s]+)\s+([^\s]+)(?:\s+.*)?$", line)
        if not match or match.group(1).lower() == "package":
            continue
        name, current, latest = match.groups()
        if current == latest:
            continue
        rows.append({"name": name, "current": current, "latest": latest, "source": "python"})
    return rows


def parse_pip_index_versions(name: str, output: str) -> dict | None:
    """Read the latest release printed by ``pip index versions``."""
    match = re.search(r"Available versions:\s*([^\n]+)", output, re.IGNORECASE)
    if not match:
        return None
    versions = [value.strip() for value in match.group(1).split(",") if value.strip()]
    if not versions:
        return None
    latest = versions[0]
    return {"name": name, "latest": latest} if latest else None


def parse_npm_outdated(output: str, project: str) -> list[dict]:
    try:
        data = json.loads(output or "{}")
    except (TypeError, json.JSONDecodeError):
        return []
    rows = []
    if not isinstance(data, dict):
        return rows
    for name, value in data.items():
        if not isinstance(value, dict):
            continue
        current, latest = value.get("current"), value.get("latest")
        if current and latest and str(current) != str(latest):
            rows.append({"name": name, "current": str(current), "latest": str(latest),
                         "source": f"npm:{project}"})
    return rows


def _major(version: str) -> int | None:
    match = re.match(r"\s*[v=]?(\d+)", version)
    return int(match.group(1)) if match else None


def is_osi_license(value: str) -> bool:
    """Accept known OSI SPDX identifiers or well-known OSI license names."""
    if not value:
        return False
    normalized = re.sub(r"\s+", "", value.lower()).replace("license", "")
    normalized = normalized.replace("(mit)", "mit").replace("bsd3clause", "bsd-3-clause")
    normalized = normalized.replace("bsd2clause", "bsd-2-clause")
    aliases = {
        "themitlicense": "mit", "apachelicense2.0": "apache-2.0", "apachev2.0": "apache-2.0",
        "bsd3-clause": "bsd-3-clause", "bsd2-clause": "bsd-2-clause", "isclicense": "isc",
        "mozilla_public_license_2.0": "mpl-2.0", "mozilla-public-license-2.0": "mpl-2.0",
        "gnu_general_public_license_v3": "gpl-3.0", "gnu_general_public_license_v2": "gpl-2.0",
        "gnu_lesser_general_public_license_v3": "lgpl-3.0", "gnu_lesser_general_public_license_v2.1": "lgpl-2.1",
    }
    normalized = aliases.get(normalized, normalized)
    # SPDX expressions may combine known licenses; reject exceptions and unknown terms.
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9.+-]*", normalized)
    terms = [token for token in tokens if token not in {"and", "or", "with"}]
    return bool(terms) and all(term in OSI_LICENSES for term in terms)


def filter_licenses(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    proposed, rejected = [], []
    for original in rows:
        row = dict(original)
        license_name = row.get("license", "")
        if is_osi_license(license_name):
            row["care"] = _major(row["current"]) is not None and _major(row["latest"]) is not None and _major(row["current"]) != _major(row["latest"])
            proposed.append(row)
        else:
            rejected.append(row)
    return proposed, rejected


def render_note(run_id: str, run_date: str, proposed: list[dict], rejected: list[dict], board: list[dict]) -> str:
    lines = [f"# Weekly maintenance proposal — {run_date}", "", f"Run: {run_id}", "",
             "This note suggests changes for the owner to review. Nothing was installed or changed.", "",
             "## Safe to update", ""]
    if proposed:
        for row in proposed:
            lines.append(f"- {row['name']}: {row['current']} → {row['latest']} ({row['source']})"
                         f" — {row['license']} licence" + ("; needs care because this changes the major version" if row.get("care") else "; no major-version jump"))
    else:
        lines.append("- No upgrades with a confirmed open-source licence were found.")
    lines.extend(["", "## Not proposed: licence", ""])
    if rejected:
        lines.extend(f"- {row['name']} ({row['source']}): {row['current']} → {row['latest']}; licence could not be confirmed as OSI open source ({row.get('license') or 'unknown'})." for row in rejected)
    else:
        lines.append("- None.")
    lines.extend(["", "## Test board", ""])
    for item in board:
        lines.append(f"- {item['name']}: {'passed' if item['passed'] else 'failed'} — {item['summary']}")
        if item.get("slowest"):
            lines.append("  - Slowest tests: " + "; ".join(item["slowest"][:5]))
    return "\n".join(lines)


def _run(command: list[str], cwd: Path, timeout: int) -> CommandResult:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return CommandResult(result.returncode, result.stdout, result.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return CommandResult(1, "", str(error))


def _network_error(result: CommandResult) -> bool:
    value = (result.stdout + "\n" + result.stderr).lower()
    return any(hint in value for hint in ("network", "resolve", "connection", "timed out", "eai_again", "enotfound"))


def _npm_outdated(project: Path, label: str, npm_command: list[str], runner, timeout: int) -> tuple[list[dict], str | None]:
    package = project / "package.json"
    if not package.is_file():
        return [], None
    result = runner(npm_command + ["outdated", "--json"], project, timeout)
    # npm outdated returns exit code 1 when packages are outdated; its JSON remains useful.
    rows = parse_npm_outdated(result.stdout, label)
    if result.returncode not in (0, 1) or (not result.stdout.strip() and result.returncode):
        return [], "could not check right now"
    return rows, None


def _license(row: dict, repo: Path, python_command: list[str], npm_command: list[str], runner, timeout: int) -> str:
    if row["source"].startswith("npm:"):
        project = repo / ("glacier/web" if row["source"] == "npm:web" else "desktop")
        result = runner(npm_command + ["view", row["name"], "license"], project, min(timeout, 60))
        return result.stdout.strip() if result.returncode == 0 else ""
    # Prefer the project's interpreter metadata, then pip show for packages not installed here.
    try:
        site_packages = repo / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        dist = next((item for item in importlib.metadata.distributions(path=[str(site_packages)])
                     if item.metadata.get("Name", "").lower().replace("_", "-") ==
                     row["name"].lower().replace("_", "-")), None)
        if dist is None:
            raise importlib.metadata.PackageNotFoundError(row["name"])
        classifiers = dist.metadata.get_all("Classifier", [])
        osi_classifier = next((item.rsplit("::", 1)[1].strip() for item in classifiers
                              if item.startswith("License :: OSI Approved ::")), "")
        metadata_license = dist.metadata.get("License-Expression") or osi_classifier or dist.metadata.get("License")
        if metadata_license:
            return metadata_license
    except importlib.metadata.PackageNotFoundError:
        pass
    # pip show is the portable metadata fallback when the distribution is not installed.
    result = runner(python_command + ["-m", "pip", "show", row["name"]], repo, min(timeout, 60))
    match = re.search(r"^License:\s*(.+)$", result.stdout, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if result.returncode == 0 and match else ""


def _test_result(name: str, result: CommandResult) -> dict:
    output = result.stdout + "\n" + result.stderr
    passed_count = sum(int(value) for value in re.findall(r"(\d+) passed", output))
    failed_count = sum(int(value) for value in re.findall(r"(\d+) failed", output))
    error_count = sum(int(value) for value in re.findall(r"(\d+) errors?", output))
    summary = f"{passed_count} passed, {failed_count} failed, {error_count} errors" if any((passed_count, failed_count, error_count)) else ("completed" if result.returncode == 0 else "could not check right now")
    slowest = []
    for line in output.splitlines():
        match = re.match(r"\s*([0-9.]+s)\s+(.+)", line)
        if match and ("::" in match.group(2) or match.group(2).startswith("test_")):
            slowest.append((float(match.group(1)[:-1]), f"{match.group(2)} ({match.group(1)})"))
    slowest = [value for _, value in sorted(slowest, reverse=True)[:5]]
    return {"name": name, "passed": result.returncode == 0, "summary": summary, "slowest": slowest}


def run_maintenance(config: RunConfig, command_runner: Callable = _run) -> dict:
    repo = config.repo.resolve()
    upgrades: list[dict] = []
    issues: list[str] = []
    pins = pinned_requirements(repo / "setup" / "requirements.txt")
    pip_result = command_runner(config.python_command + ["-m", "pip", "list", "--outdated", "--format=columns"], repo, config.timeout)
    if pip_result.returncode == 0:
        rows = {row["name"].lower().replace("_", "-"): row for row in parse_pip_outdated(pip_result.stdout)}
        for pin in pins:
            name = pin.split("==", 1)[0].strip()
            row = rows.get(name.lower().replace("_", "-"))
            if row:
                upgrades.append(row)
            else:
                # pip list may omit index failures; the pinned requirement provides a safe
                # fallback query while keeping all checks read-only.
                result = command_runner(config.python_command + ["-m", "pip", "index", "versions", name], repo, min(config.timeout, 60))
                version = parse_pip_index_versions(name, result.stdout + "\n" + result.stderr) if result.returncode == 0 else None
                current = pin.split("==", 1)[1].split(";", 1)[0].strip()
                if version and version["latest"] != current:
                    upgrades.append({"name": name, "current": current, "latest": version["latest"], "source": "python"})
                elif result.returncode:
                    issues.append(f"Python package check for {name}: could not check right now.")
    else:
        issues.append("Python package check: could not check right now.")
    for relative, label in (("glacier/web", "web"), ("desktop", "desktop")):
        rows, issue = _npm_outdated(repo / relative, label, config.npm_command, command_runner, config.timeout)
        upgrades.extend(rows)
        if issue:
            issues.append(f"{label.title()} package check: {issue}.")

    licensed = []
    for row in upgrades:
        license_name = _license(row, repo, config.python_command, config.npm_command, command_runner, config.timeout)
        row["license"] = license_name or "unknown"
        if not license_name:
            issues.append(f"Licence check for {row['name']}: could not check right now; not proposed until confirmed.")
        licensed.append(row)
    proposed, rejected = filter_licenses(licensed)

    board = []
    board.append(_test_result("Backend tests", command_runner(config.backend_command, repo / "glacier/backend", config.timeout)))
    board.append(_test_result("Screen check", command_runner(config.ui_command, repo / "glacier/web", config.timeout)))
    note = render_note(config.run_id, config.date, proposed, rejected, board)
    if issues:
        note = note.replace("## Not proposed: licence", "## Checks that could not run\n\n" + "\n".join(f"- {item}" for item in issues) + "\n\n## Not proposed: licence")
    path = f"proposals/maintenance-{config.date}.md"
    return {"path": path, "body": note, "author": f"run:{config.run_id}"}


def pinned_requirements(path: Path) -> list[str]:
    if not path.is_file():
        return []
    pins = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value and "==" in value and not value.startswith(("-", "git+", "http:")):
            pins.append(value)
    return pins


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a proposal-only weekly maintenance note.")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--run", required=True)
    parser.add_argument("--api", default=os.environ.get("GLACIER_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    python = str(args.repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    if not Path(python).is_file():
        python = sys.executable
    config = RunConfig(args.repo, args.run, date_type.today().isoformat(), [python], ["npm"],
                       [python, "-m", "pytest", "-q", "--durations=5", "tests"],
                       ["npm", "run", "check:ui"], args.timeout)
    try:
        result = run_maintenance(config)
        print(result["body"])
    except (OSError, ValueError) as error:
        print(f"Could not prepare the maintenance proposal: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
