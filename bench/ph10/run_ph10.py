#!/usr/bin/env python3
"""Run the existing PH10 acceptance checks and print a compact result table."""
from __future__ import annotations

import os
from pathlib import Path
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"
BACKEND = ROOT / "glacier" / "backend"
WEB = ROOT / "glacier" / "web"
RESULTS: list[tuple[str, str, str]] = []


def run(label: str, command: list[str], cwd: Path = ROOT, missing_detail: str = "") -> None:
    print(f"\n[{label}] $ {' '.join(shlex.quote(part) for part in command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd, env=os.environ.copy())
    detail = "" if completed.returncode == 0 else f"exit {completed.returncode}"
    if completed.returncode != 0 and missing_detail:
        detail += f"; {missing_detail}"
    RESULTS.append((label, "PASS" if completed.returncode == 0 else "FAIL", detail))


def pytest(label: str, nodeids: list[str]) -> None:
    run(label, [str(PYTHON), "-m", "pytest", "-q", *nodeids], BACKEND)


def run_remaining_templates() -> None:
    """Apply/run the ten original templates against the backend's fake Codex and safe command stand-ins."""
    template_dir = ROOT / "templates"
    templates = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(template_dir.glob("tpl-*.json"))]
    everyday = {"tpl-document-note", "tpl-downloads-tidy", "tpl-meeting-tasks",
                "tpl-web-change-watch", "tpl-morning-brief", "tpl-backup-check"}
    candidates = [flow for flow in templates if flow["id"] not in everyday]
    try:
        # Reuse the same backend subprocess/test helpers as the existing integration harness.
        sys.path.insert(0, str(BACKEND / "tests"))
        sys.path.insert(0, str(BACKEND))
        import conftest  # type: ignore[import-not-found]

        with tempfile.TemporaryDirectory(prefix="ph10-templates-") as temp:
            home = Path(temp)
            shim = home / "standins"
            shim.mkdir()
            # These templates request a general test command or public website probe. The stand-ins
            # return success without running arbitrary project code or making network requests.
            for name, body in {
                "python3": "#!/bin/sh\nif [ \"$1\" = \"-m\" ] && [ \"$2\" = \"pytest\" ]; then exit 0; fi\nexec /usr/bin/python3 \"$@\"\n",
                "curl": "#!/bin/sh\nexit 0\n",
            }.items():
                path = shim / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)
            codex = shim / "codex"
            codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, subprocess, sys\n"
                "args = sys.argv[1:]\n"
                "if '--output-schema' in args:\n"
                "    schema = json.load(open(args[args.index('--output-schema') + 1], encoding='utf-8'))\n"
                "    output = args[args.index('-o') + 1]\n"
                "    choice = schema['properties']['choice']['enum'][0]\n"
                "    with open(output, 'w', encoding='utf-8') as stream: json.dump({'choice': choice}, stream)\n"
                "    raise SystemExit(0)\n"
                f"raise SystemExit(subprocess.call([{str(BACKEND / 'tests' / 'fake_codex.py')!r}, *args]))\n",
                encoding="utf-8",
            )
            codex.chmod(0o755)
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = str(shim) + os.pathsep + old_path
            try:
                conftest.FAKE_CODEX = str(codex)
                server = conftest.Server(home).start()
                try:
                    # Install all bundled flows before starting any, so the sub-flow example can run.
                    for flow in templates:
                        flow = json.loads(json.dumps(flow))
                        for node in flow["nodes"]:
                            config = node.setdefault("config", {})
                            if node["type"] == "decide":
                                config["engine"] = "codex"
                            if node["type"] == "command":
                                command = config.get("cmd", "")
                                if "pytest" in command:
                                    config["cmd"] = "python3 -m pytest -q"
                                elif "curl" in command:
                                    config["cmd"] = "curl --fail https://example.invalid"
                        server.put(f"/api/environments/{flow['id']}", flow)
                    for flow in candidates:
                        template_id = flow["id"]
                        try:
                            run_id = server.post(f"/api/environments/{template_id}/run")["run_id"]
                            deadline = time.time() + 60
                            approved_nodes: set[str] = set()
                            while time.time() < deadline:
                                current = server.get(f"/api/runs/{run_id}")
                                if current["status"] == "waiting":
                                    node_id = current.get("waiting_on")
                                    if node_id and node_id not in approved_nodes:
                                        server.post(f"/api/runs/{run_id}/approve", {"node_id": node_id, "approved": True})
                                        approved_nodes.add(node_id)
                                elif current["status"] in ("done", "failed", "rejected"):
                                    break
                                time.sleep(0.2)
                            result = server.get(f"/api/runs/{run_id}")
                            ok = result["status"] == "done"
                            detail = "" if ok else f"status={result['status']}; stand-ins could not complete this flow"
                            RESULTS.append((f"template {template_id}", "PASS" if ok else "FAIL", detail))
                        except Exception as exc:
                            RESULTS.append((f"template {template_id}", "FAIL", f"{type(exc).__name__}: {exc}"))
                finally:
                    server.stop()
            finally:
                os.environ["PATH"] = old_path
    except Exception as exc:
        for flow in candidates:
            RESULTS.append((f"template {flow['id']}", "FAIL", f"harness unavailable: {type(exc).__name__}: {exc}"))


def main() -> int:
    # Guide links and screen help destinations are checked from source and docs.
    run("guide links and screen help", [str(PYTHON), str(ROOT / "bench/ph10/check_docs.py")])

    # Reuse the shipped provenance and safety checks, then execute every template.
    run("template manifest and review", [str(PYTHON), "-m", "pytest", "-q", "tests/test_template_registry.py::test_manifest_hashes_match_all_bundled_templates"], BACKEND)
    run("template structure and safety", [str(PYTHON), "-m", "pytest", "-q", "templates/test_templates.py"], ROOT)
    six = subprocess.run([str(PYTHON), "-m", "pytest", "-q", "tests/test_templates_more.py::test_six_templates_run_with_user_settings_and_prove_real_outcomes"], cwd=BACKEND, env=os.environ.copy())
    RESULTS.append(("six everyday templates stand-in run", "PASS" if six.returncode == 0 else "FAIL", "" if six.returncode == 0 else f"exit {six.returncode}"))
    if six.returncode == 0:
        for template_id in sorted({"tpl-document-note", "tpl-downloads-tidy", "tpl-meeting-tasks",
                                   "tpl-web-change-watch", "tpl-morning-brief", "tpl-backup-check"}):
            RESULTS.append((f"template {template_id}", "PASS", "existing stand-in harness reached verified done"))
    run_remaining_templates()

    run("English/Spanish keys and placeholders", ["bash", str(Path.home() / "tools" / "e2e.sh"), "node", "scripts/check-i18n.mjs", "--fail"], WEB)
    spanish = WEB / "e2e" / "spanish.spec.mjs"
    run("Spanish screen", ["bash", str(Path.home() / "tools" / "e2e.sh"), "node", "e2e/spanish.spec.mjs"], WEB,
        "e2e/spanish.spec.mjs is absent from this worktree" if not spanish.is_file() else "")

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
