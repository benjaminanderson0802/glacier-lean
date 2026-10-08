#!/usr/bin/env python3
"""Recheck the PH0 foundation claims against this checkout."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "setup"))
import health_check  # noqa: E402 - reuse the repository's pinned-requirement reader
PYTHON_TOOLS = {
    "DBOS": ("dbos", "dbos"),
    "ACP": ("agent-client-protocol", "acp"),
    "vault + git + search": ("gitpython", "git"),
}
JS_TOOLS = {
    "React Flow": "@xyflow/react", "xterm": "@xterm/xterm",
}
LICENSES_PATH = ROOT / "setup/licenses.json"


def req_pins() -> dict[str, str]:
    rows = {}
    for line in health_check.pinned_requirements():
        match = re.match(r"\s*([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if match:
            rows[match.group(1).lower().replace("_", "-")] = match.group(2)
    return rows


def license_records() -> dict[str, dict[str, str]]:
    """Read SPDX identifiers recorded from package metadata or upstream licences."""
    value = json.loads(LICENSES_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("packages"), list):
        raise ValueError("setup/licenses.json must contain a packages list")
    return {
        row["distribution"].lower().replace("_", "-"): row
        for row in value["packages"]
        if isinstance(row, dict) and isinstance(row.get("distribution"), str)
    }


def py_tool_rows() -> list[tuple[str, bool, str]]:
    pins = req_pins()
    try:
        records = license_records()
        records_error = ""
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
        records, records_error = {}, f"; licence records unavailable: {error}"
    rows = []
    for name, (distribution, module) in PYTHON_TOOLS.items():
        normalized = distribution.lower().replace("_", "-")
        pin = pins.get(normalized)
        try:
            version = importlib.metadata.version(distribution)
            metadata = importlib.metadata.metadata(distribution)
            license_name = metadata.get("License-Expression") or metadata.get("License") or ""
            source = "package metadata"
            if not license_name:
                record = records.get(normalized, {})
                if record.get("version") == version:
                    license_name = record.get("spdx", "")
                    source = "setup/licenses.json"
            if not license_name:
                license_name, source = "unrecorded", "no matching record"
            __import__(module)
            ok = bool(pin and version == pin and license_name != "unrecorded")
            detail = f"{distribution}=={version}; pin={pin or 'missing'}; licence={license_name} ({source}); import={module}{records_error}"
        except Exception as error:
            ok, detail = False, f"{distribution}; pin={pin or 'missing'}; import/metadata error: {error}"
        rows.append((name, ok, detail))
    return rows


def run_replacement_tests(paths: list[str]) -> tuple[bool, str]:
    """Run existing tests for a replacement before counting it as PH0 proof."""
    command = [sys.executable, "-m", "pytest", "-q", *paths]
    try:
        result = subprocess.run(command, cwd=ROOT / "glacier/backend", text=True,
                                capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"replacement tests could not run: {error}"
    output = (result.stdout + result.stderr).strip().splitlines()
    summary = output[-1] if output else "no pytest output"
    return result.returncode == 0, summary


def run_editor_replacement_check() -> tuple[bool, str]:
    """Build and run the existing screen check for the plain text editor replacement."""
    web = ROOT / "glacier/web"
    try:
        build = subprocess.run(["npm", "run", "build"], cwd=web, text=True,
                               capture_output=True, timeout=180, check=False)
        if build.returncode:
            lines = (build.stdout + build.stderr).strip().splitlines()
            return False, lines[-1] if lines else "npm build failed"
        helper = Path.home() / "tools/e2e.sh"
        if not helper.is_file():
            return False, "screen test helper ~/tools/e2e.sh is unavailable"
        command = ["bash", str(helper), "node", "e2e/shell.spec.mjs"]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                timeout=300, check=False)
        retried = result.returncode != 0
        if retried:
            # A fresh browser/server process handles transient startup races. This
            # remains a failure unless a complete, unchanged E2E check passes.
            time.sleep(2)  # Let the previous browser and port cleanup finish.
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                    timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"editor replacement check could not run: {error}"
    output = (result.stdout + result.stderr).strip().splitlines()
    summary = next((line for line in reversed(output)
                    if "timeout" in line.lower() or "error" in line.lower()),
                   next((line for line in reversed(output) if "shell" in line.lower()),
                        output[-1] if output else "no screen-test output"))
    if retried and result.returncode == 0:
        summary = f"fresh-process retry passed after an initial failure: {summary}"
    return result.returncode == 0, summary


def replacement_rows() -> list[tuple[str, bool, str]]:
    maf_tests = ["tests/test_core.py", "tests/test_local_ai.py", "tests/test_acp_agent.py"]
    maf_passed, maf_detail = run_replacement_tests(maf_tests)
    maf = ("MAF workflows", maf_passed,
           f"replaced by DBOS workflows + local model/ACP adapters (PRs #6, #10); "
           f"checked via {', '.join(Path(path).name for path in maf_tests)}: {maf_detail}")

    gateway_tests = ["tests/test_gateway.py"]
    gateway_passed, gateway_detail = run_replacement_tests(gateway_tests)
    gateway_source = ROOT / "glacier/backend/gateway.py"
    gateway = ("Bifrost", gateway_passed and gateway_source.is_file(),
               f"replaced by Glacier built-in model gateway (PR #19); "
               f"checked gateway.py + test_gateway.py: {gateway_detail}; Bifrost remains optional")

    agui_tests = ["tests/test_assistant_chat.py", "tests/test_ask_local_route.py"]
    agui_passed, agui_detail = run_replacement_tests(agui_tests)
    api_source = ROOT / "glacier/web/src/api.ts"
    agui = ("AG-UI", agui_passed and api_source.is_file(),
            f"replaced by Glacier's native AG-UI event client (PRs #28, #52); "
            f"checked via {', '.join(Path(path).name for path in agui_tests)}: {agui_detail}")

    editor_passed, editor_detail = run_editor_replacement_check()
    editor = ("Monaco", editor_passed,
              f"replaced by the plain text note editor (PR #54); checked shell.spec.mjs: {editor_detail}")
    return [maf, gateway, agui, editor]


def js_tool_rows() -> list[tuple[str, bool, str]]:
    package = json.loads((ROOT / "glacier/web/package.json").read_text(encoding="utf-8"))
    pins = package.get("dependencies", {})
    rows = []
    for name, package_name in JS_TOOLS.items():
        manifest = ROOT / "glacier/web/node_modules" / package_name / "package.json"
        try:
            installed = json.loads(manifest.read_text(encoding="utf-8"))
            pin = pins.get(package_name)
            version = installed.get("version")
            license_name = installed.get("license") or "unrecorded"
            ok = bool(pin and version == pin and license_name != "unrecorded")
            detail = f"{package_name}@{version}; pin={pin or 'missing'}; licence={license_name}"
        except Exception as error:
            ok, detail = False, f"{package_name}; package metadata unavailable: {error}"
        rows.append((name, ok, detail))
    return rows


def legacy_rows() -> list[tuple[str, bool, str]]:
    map_path = ROOT / "docs/OLD_CODE_MAP.md"
    if not map_path.is_file():
        return [("legacy code map", False, "docs/OLD_CODE_MAP.md missing")]
    text = map_path.read_text(encoding="utf-8")
    checked, missing, keepers = 0, [], []
    # Source-path rows in the old module inventory are named with backticks.
    for match in re.finditer(r"^\| `([^`]+)` \|[^\n]*\| (DELETE(?:-UNNEEDED)?|KEEP(?:/PORT[^|]*)?) \|", text, re.M):
        path, verdict = match.groups()
        if path.startswith(("C:\\", "ui/assets/")) or "*" in path:
            continue
        checked += 1
        candidates = [ROOT / path, ROOT / "legacy-keep" / path]
        if verdict.startswith("KEEP"):
            present = next((p for p in candidates if p.exists()), None)
            if present is None:
                missing.append(path)
            else:
                keepers.append(path)
        elif any(p.exists() for p in candidates):
            missing.append(f"{path} remains outside a documented keeper")
    ok = checked > 0 and not missing
    detail = f"{checked} mapped entries checked; {len(keepers)} keepers found under legacy-keep or repo root"
    if missing:
        detail += "; unresolved: " + ", ".join(missing[:5])
    return [("legacy paths mapped or removed", ok, detail)]


def repo_rows() -> list[tuple[str, bool, str]]:
    required = [".devcontainer/devcontainer.json", "setup/requirements.txt", "setup/health_check.py",
                "glacier/backend", "glacier/web", "evidence/RESULTS.md"]
    missing = [item for item in required if not (ROOT / item).exists()]
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                                text=True, capture_output=True, check=False)
        git_ok = result.returncode == 0 and Path(result.stdout.strip()).resolve() == ROOT
        git_detail = f"root={result.stdout.strip()}"
    except OSError as error:
        git_ok, git_detail = False, str(error)
    expected_python = health_check.current_python().resolve()
    return [("sandbox/repo setup", not missing and git_ok,
             f"devcontainer, health check, pinned requirements, backend/web and historical results present; "
             f"health-check interpreter={expected_python}; {git_detail}" +
             (f"; missing={missing}" if missing else ""))]


def prior_system_rows() -> list[tuple[str, bool, str]]:
    """Inspect this checkout for old autonomous service/config entry points."""
    try:
        result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                                capture_output=True, check=True)
        tracked = result.stdout.decode().split("\0")
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        return [("prior systems disabled", False, f"could not inspect tracked paths: {error}")]
    tracked = [path for path in tracked if path]
    stale_path_patterns = (".forge/", "forge/", "setup/forge", "docker-compose.", "compose.yaml", "compose.yml")
    stale_paths = [path for path in tracked if any(part in path.lower() for part in stale_path_patterns)]
    active_roots = ("setup/", ".github/workflows/", ".devcontainer/")
    active_suffixes = (".sh", ".ps1", ".yml", ".yaml", ".json", ".toml")
    markers = ("glaciercampaign", "forge tasks", "forge_tasks", "forgetask")
    references = []
    for relative in tracked:
        if not relative.startswith(active_roots) or not relative.endswith(active_suffixes):
            continue
        try:
            body = (ROOT / relative).read_text(encoding="utf-8").lower()
        except (OSError, UnicodeError):
            references.append(relative + " (unreadable)")
            continue
        if any(marker in body for marker in markers):
            references.append(relative)
    ok = not stale_paths and not references
    if ok:
        detail = (f"checked {len(tracked)} tracked paths and setup/deployment configs; "
                  "no Forge task launch config or legacy container orchestration files")
    else:
        detail = f"legacy config paths={stale_paths}; launch references={references}"
    return [("prior systems disabled", ok, detail)]


def main() -> int:
    rows = py_tool_rows() + replacement_rows() + js_tool_rows() + repo_rows() + legacy_rows() + prior_system_rows()
    print("PH0 repeatable proof")
    print(f"{'STATUS':<7} | {'CLAIM':<34} | EVIDENCE")
    print("--------+------------------------------------+" + "-" * 78)
    for name, passed, detail in rows:
        print(f"{'PASS' if passed else 'FAIL':<7} | {name:<34} | {detail}")
    return 0 if all(passed for _, passed, _ in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
