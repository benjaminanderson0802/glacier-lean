#!/usr/bin/env python3
"""Recheck the PH0 foundation claims against this checkout."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "setup"))
import health_check  # noqa: E402 - reuse the repository's pinned-requirement reader
PYTHON_TOOLS = {
    "MAF workflows": ("agent-framework-core", "agent_framework"),
    "DBOS": ("dbos", "dbos"),
    "ACP": ("agent-client-protocol", "acp"),
    "Bifrost": ("bifrost", "bifrost"),
    "vault + git + search": ("gitpython", "git"),
}
JS_TOOLS = {
    "AG-UI": "@ag-ui/client", "React Flow": "@xyflow/react",
    "xterm": "@xterm/xterm", "Monaco": "@monaco-editor/react",
}


def req_pins() -> dict[str, str]:
    rows = {}
    for line in health_check.pinned_requirements():
        match = re.match(r"\s*([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if match:
            rows[match.group(1).lower().replace("_", "-")] = match.group(2)
    return rows


def py_tool_rows() -> list[tuple[str, bool, str]]:
    pins = req_pins()
    rows = []
    for name, (distribution, module) in PYTHON_TOOLS.items():
        pin = pins.get(distribution.lower())
        try:
            version = importlib.metadata.version(distribution)
            license_name = (importlib.metadata.metadata(distribution).get("License-Expression")
                            or importlib.metadata.metadata(distribution).get("License") or "unrecorded")
            __import__(module)
            ok = bool(pin and version == pin and license_name != "unrecorded")
            detail = f"{distribution}=={version}; pin={pin or 'missing'}; licence={license_name}; import={module}"
        except Exception as error:
            ok, detail = False, f"{distribution}; pin={pin or 'missing'}; import/metadata error: {error}"
        rows.append((name, ok, detail))
    return rows


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
    # PH0.4's only evidence is a historical session log; there is no current
    # machine-readable switch or inventory for Forge tasks/container systems.
    evidence = "NORTHSTAR PH0.4 cites only the 2026-10-06 session log; current disabled state is not inspectable"
    return [("prior systems disabled", False, evidence)]


def main() -> int:
    rows = py_tool_rows() + js_tool_rows() + repo_rows() + legacy_rows() + prior_system_rows()
    print("PH0 repeatable proof")
    print(f"{'STATUS':<7} | {'CLAIM':<34} | EVIDENCE")
    print("--------+------------------------------------+" + "-" * 78)
    for name, passed, detail in rows:
        print(f"{'PASS' if passed else 'FAIL':<7} | {name:<34} | {detail}")
    return 0 if all(passed for _, passed, _ in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
