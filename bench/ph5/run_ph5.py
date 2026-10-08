#!/usr/bin/env python3
"""Run the PH5 assistant, screen, and verification checks as one proof."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "glacier" / "backend"
WEB = ROOT / "glacier" / "web"
PYTHON = Path(os.environ.get("GLACIER_PYTHON") or sys.executable)


def run(label: str, command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd or ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    return result.returncode, output


def pytest_group(name: str, nodes: list[str]) -> tuple[str, bool, str]:
    code, output = run(name, [str(PYTHON), "-m", "pytest", "-q", *nodes], BACKEND)
    found = re.search(r"(\d+ passed(?:, \d+ skipped)?|\d+ failed(?:, .*?)?)(?: in [\d.]+s)?\s*$", output, re.M)
    count = found.group(1) if found else ("no summary" if not output else output.splitlines()[-1])
    return name, code == 0, count


def main() -> int:
    rows: list[tuple[str, bool, str]] = []
    groups = [
        ("assistant planner", ["tests/test_assistant.py"]),
        ("assistant chat", ["tests/test_assistant_chat.py"]),
        ("Ask routes", ["tests/test_ask_local_route.py"]),
        ("proposals and Ask-runs", ["tests/test_assistant_chat_runs.py", "tests/test_claim_rerun.py"]),
    ]
    for name, nodes in groups:
        rows.append(pytest_group(name, nodes))

    build_code, build_output = run("build screen for e2e", ["npm", "run", "-s", "build"], WEB)
    if build_code == 0:
        e2e = ["node", "e2e/shell.spec.mjs"]
        code, output = run("Ask and Simple/Standard/Full screen", ["bash", str(Path.home() / "tools" / "e2e.sh"), *e2e], WEB)
    else:
        code, output = build_code, build_output
    rows.append(("Ask and layouts screen", code == 0, "PASS" if code == 0 else output.splitlines()[-1] if output else f"exit {code}"))

    env = os.environ.copy()
    env["GLACIER_PYTHON"] = str(PYTHON)
    code, output = run("verification benchmark", [str(PYTHON), "bench/verification/run_glacier.py"], ROOT, env)
    false_match = re.search(r"False-done rate: ([\d.]+)% \((\d+)/(\d+)", output)
    verified_match = re.search(r"Verified rate: ([\d.]+)% \((\d+)/(\d+)", output)
    numbers = "metrics unavailable"
    threshold_pass = False
    if false_match and verified_match:
        false_rate = float(false_match.group(1))
        verified_rate = float(verified_match.group(1))
        numbers = f"false-done {false_match.group(2)}/{false_match.group(3)} ({false_rate:.2f}%); verified {verified_match.group(2)}/{verified_match.group(3)} ({verified_rate:.2f}%)"
        threshold_pass = false_rate < 2.0 and verified_rate >= 98.0
    rows.append(("M-FALSE-DONE / M-VERIFIED", code == 0 and threshold_pass, numbers))

    width = max(len(row[0]) for row in rows)
    print("\nPH5 RESULT TABLE")
    print(f"{'Check':<{width}} | Result | Numbers")
    print(f"{'-' * width}-+--------+---------")
    for name, passed, numbers in rows:
        print(f"{name:<{width}} | {'PASS' if passed else 'FAIL':<6} | {numbers}")
    return 0 if all(passed for _, passed, _ in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
