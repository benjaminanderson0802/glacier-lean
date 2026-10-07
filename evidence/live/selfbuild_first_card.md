# First live self-build card

## Result

- Checkpoint: PH9.2, attempted; not complete.
- Run ID: `ea0a71bb2629`.
- Started: 2026-10-07 21:04:09 UTC. Terminal at 21:06:45 UTC; total 155.655 seconds.
- Backend: local Uvicorn on `127.0.0.1:8765`, using the project `.venv` and fresh `GLACIER_HOME=/tmp/glacier-w31-selfbuild-home`. The generated engine token stayed in that folder and was not printed.
- Worker: Codex CLI, already logged in. The existing Codex config selected `gpt-6-luna`, low reasoning effort. The run reported route `codex/chatgpt-plan`, zero cost, 193,226 input tokens and 1,439 output tokens.
- Checkout: `$GLACIER_HOME/workspaces/self-feature`, a local scratch clone. Worker branch: `run/ea0a71bb2629`. No push occurred.
- Final state: failed, `verified: false`, `merged: false`. Scratch clone `main` stayed at `fd0a239ad0e45342cdf9dd5020317ebfb6f6655c` (`Add recovery benchmark (#42)`). The worker diff remains on its isolated branch and was not copied into this branch.

The worker completed and produced the requested two-file diff. The first configured acceptance command, the protected-path guard, could not start because the backend process could not resolve the bare command `python`. All later command checks also failed for that same reason. The guard itself therefore did not evaluate the diff. Reviewing the unchanged guard configuration shows that `setup/health_check.py` is protected, so this diff would be rejected by that guard if it ran. That conclusion is from reading the configured guard globs, not from a guard execution.

## Drift check

1. This advances PH9.2, Glacier’s feature flow. The attempt does not satisfy the checkpoint.
2. PH3 and PH7 have approved exits. PH5 remains in progress; NORTHSTAR explicitly allows PH9 self-build only with owner approval and verified-merge-only while dependencies remain unfinished.
3. It serves P-VERIFY and P-GOALS, with M-VERIFIED and M-INTERVENE relevant to this run.
4. The existing open-source feature flow already performs isolated work, independent checks, and guarded local merging. This card uses that flow; it adds no replacement tool.
5. Acceptance: run this real card through the documented feature flow; require the protected guard, backend suite, other project suites, verification benchmark, security benchmark, and final owner check to pass before a local merge. The flow did not pass this acceptance test.

## Flow steps

Durations below come from DBOS operation timestamps in the temporary home. Approval waits include time waiting for the API decision.

| Step | Status | Duration | Record |
| --- | --- | ---: | --- |
| Prepare isolated workspace | done | 0.053 s | Worktree created at `worktrees/self-feature/ea0a71bb2629`. |
| Load card | done | 0.010 s | Card text matched `setup/selfbuild/cards/health-version.md`. |
| Start approval wait | approved | 31.805 s | Approved by API after reviewing the card and confirming the work was isolated, local-only, and limited to the requested feature. |
| Finish start approval | done | 0.009 s | API approval was recorded. |
| Codex worker | done, exit 0 | 24.919 s | Worker reported the two-file diff. It said its test could not run because the project interpreter path was unavailable and system Python had no pytest; it reported `git diff --check` passed. |
| Worker result check | done | 0.042 s | Worker exit code was zero. |
| Feature report note | done | 0.240 s | Saved as `self-build/feature-ea0a71bb2629.md` in the temporary vault. |
| Protected-path guard command | failed to launch | 0.364 s | `/bin/sh: 1: python: not found` — the guard script did not execute. |
| Backend suite acceptance command | failed to launch | 0.142 s | `/bin/sh: 1: python: not found` |
| Other suites acceptance command | failed to launch | 0.133 s | `/bin/sh: 1: python: not found` |
| Verification benchmark command | failed to launch | 0.240 s | `/bin/sh: 1: python: not found` |
| Security benchmark command | failed to launch | 0.157 s | `/bin/sh: 1: python: not found` |
| Final owner check wait | rejected | 95.961 s | Rejected through the API because the protected-path guard and all command checks had failed to launch. The prompt requires approval only after reviewing the protected-path list; the guard had printed no list or verdict. |
| Finish owner check | rejected | 0.010 s | API recorded `rejected by the owner`. |
| Finish workspace | done | 0.018 s | Isolated branch kept for inspection; no merge. |
| Finish run | failed | 0.009 s | `verified: false`, `merged: false`. |

### API approval decisions

1. `approve_start` — approved (`POST /api/runs/ea0a71bb2629/approve`, node `approve_start`). Reason: the card was the assigned PH9.2 trial, its scope was small, and the feature flow limits work to an isolated local branch with no push.
2. `check-5` — rejected through the same API. Reason: the required acceptance commands had failed, the guard had not run, and there was no basis to approve a verified merge.

No other approval was requested or given. The backend token was read only by the local API client and was never printed.

## Worker diff (not merged)

```diff
diff --git a/setup/health_check.py b/setup/health_check.py
index 863c4d6..cd8823e 100644
--- a/setup/health_check.py
+++ b/setup/health_check.py
@@ -206,6 +206,9 @@ def print_report(report: dict) -> None:
 def main(argv: list[str] | None = None) -> int:
     parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--version", action="version",
+                        version=json.loads((REPO / "glacier" / "web" / "package.json").read_text(
+                            encoding="utf-8"))["version"])
     parser.add_argument("--quick", action="store_true", help="reuse the current Python environment")
     parser.add_argument("--report", type=Path, help="JSON report path (defaults to setup/.health/health-report.json)")
     args = parser.parse_args(argv)
diff --git a/setup/test_health_check.py b/setup/test_health_check.py
index 7ede934..8726d4f 100644
--- a/setup/test_health_check.py
+++ b/setup/test_health_check.py
@@ -33,6 +33,20 @@ def test_report_shape_and_success_exit(monkeypatch, tmp_path, capsys):
     assert "Health check passed" in capsys.readouterr().out

+
+def test_version_prints_app_version_and_exits_zero(capsys):
+    version = json.loads((health_check.REPO / "glacier" / "web" / "package.json").read_text(
+        encoding="utf-8"))["version"]
+
+    try:
+        health_check.main(["--version"])
+    except SystemExit as exit_result:
+        assert exit_result.code == 0
+    else:
+        raise AssertionError("--version should exit")
+
+    assert capsys.readouterr().out.strip() == version
+

 def test_failed_section_writes_failed_report_and_exits_one(monkeypatch, tmp_path, capsys):
```

## Human work and follow-up

The human work for this attempt was reviewing the loaded card, approving its start, then rejecting the final gate when the configured checks failed. No manual code edits were made to the run branch, and no product code was copied into this branch.

The environment needs the project `.venv/bin` on `PATH` before starting the backend, because the saved acceptance commands call `python` by name. A future attempt also needs an owner decision about the card/guard conflict: the requested implementation file is currently protected. This run was not retried, and neither issue was worked around.

## Separate backend suite required by the card

This is the explicit card-level full-suite run, separate from the failed acceptance command above. It waited for the shared lock, then ran the required command:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ../../.venv/bin/python -m pytest -q tests'
```

Exact final line:

```text
412 passed, 1 warning in 555.90s (0:09:15)
```
