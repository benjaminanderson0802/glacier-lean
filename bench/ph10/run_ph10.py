#!/usr/bin/env python3
"""Run the existing PH10 acceptance checks and print a compact result table."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"
BACKEND = ROOT / "glacier" / "backend"
WEB = ROOT / "glacier" / "web"
RESULTS: list[tuple[str, str, str]] = []


def run(label: str, command: list[str], cwd: Path = ROOT) -> None:
    print(f"\n[{label}] $ {' '.join(shlex.quote(part) for part in command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd, env=os.environ.copy())
    RESULTS.append((label, "PASS" if completed.returncode == 0 else "FAIL", "" if completed.returncode == 0 else f"exit {completed.returncode}"))


def pytest(label: str, nodeids: list[str]) -> None:
    run(label, [str(PYTHON), "-m", "pytest", "-q", *nodeids], BACKEND)


def main() -> int:
    # Guide links and screen help destinations are checked from source and docs.
    run("guide links and screen help", [str(PYTHON), str(ROOT / "bench/ph10/check_docs.py")])

    # Reuse the shipped provenance and stand-in execution tests. The current
    # stand-in harness runs six everyday templates; expose that count plainly.
    run("template manifest and review", [str(PYTHON), "-m", "pytest", "-q", "tests/test_template_registry.py::test_manifest_hashes_match_all_bundled_templates"], BACKEND)
    run("template structure and safety", [str(PYTHON), "-m", "pytest", "-q", "templates/test_templates.py"], ROOT)
    run("template stand-in runs (6)", [str(PYTHON), "-m", "pytest", "-q", "tests/test_templates_more.py::test_six_templates_run_with_user_settings_and_prove_real_outcomes"], BACKEND)
    RESULTS.append(("all 16 templates run", "FAIL", "existing stand-in harness executes 6 of 16; no harness for remaining 10"))

    if (WEB / "node_modules" / "typescript").exists():
        run("English/Spanish keys and placeholders", ["node", "scripts/check-i18n.mjs", "--fail"], WEB)
    else:
        RESULTS.append(("English/Spanish keys and placeholders", "SKIPPED", "web TypeScript dependency is unavailable"))
    e2e = Path.home() / "tools" / "e2e.sh"
    spanish = WEB / "e2e" / "spanish.spec.mjs"
    if e2e.is_file() and spanish.is_file() and (WEB / "node_modules" / "playwright").exists():
        run("Spanish screen", ["bash", str(e2e), "node", f"e2e/{spanish.name}"], WEB)
    else:
        missing = [str(p) for p in (e2e, spanish) if not p.is_file()]
        if not (WEB / "node_modules" / "playwright").exists():
            missing.append("web Playwright dependency unavailable")
        reason = "missing " + ", ".join(missing)
        RESULTS.append(("Spanish screen", "SKIPPED", reason))

    pytest("flow export/import", ["tests/test_portable.py::test_export_import_round_trip_equals_input"])
    pytest("A2A", ["tests/test_a2a.py"])
    pytest("MCP memory server", ["tests/test_mcp_interop.py"])
    pytest("ACP stand-in", ["tests/test_acp_harnesses.py::test_two_different_agents_complete_same_goal_and_keep_security"])
    pytest("AG-UI events", ["tests/test_assistant_chat.py::test_chat_stream_has_ordered_ag_ui_events"])
    pytest("AGENTS.md", ["tests/test_agents_md.py"])

    print("\nPH10 acceptance results")
    print("Check                              Result   Details")
    print("---------------------------------  -------  -----------------------------------------------")
    for label, status, detail in RESULTS:
        print(f"{label:<34} {status:<8} {detail}")
    return 1 if any(status == "FAIL" for _, status, _ in RESULTS) else 0


if __name__ == "__main__":
    raise SystemExit(main())
