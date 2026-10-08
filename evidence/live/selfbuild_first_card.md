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


# Retry: scanner source-list card

## Result

- Checkpoint: PH9.2, attempted; not complete.
- Run ID: `22c344e628ad`.
- Started: 2026-10-07 21:37:34 UTC; final state observed 21:40:18 UTC (about 164 seconds).
- Backend: local Uvicorn at `127.0.0.1:8765`, project interpreter `/home/glacier/w/glacier-lean/.venv/bin/python`, temporary `GLACIER_HOME=/tmp/glacier-w31-retry-home`. Its engine token stayed in the temporary home and was not printed.
- Worker: Codex CLI using the existing login and configured `gpt-6-luna`, low reasoning effort. Route `codex/chatgpt-plan`; cost `$0.00`; 326,117 input tokens and 1,727 output tokens.
- Scratch checkout: `/tmp/glacier-w31-retry-home/workspaces/self-feature`. Worker branch `run/22c344e628ad`, commit `d306a4e`; scratch `main` stayed unchanged. No push occurred.
- Final state: failed, `verified: false`, `merged: false`. No product feature diff was copied into this branch because required checks failed.

The guard command failed before running because the acceptance engine left `{guard}` and `{baseline}` literal. The backend-suite command failed because it still used bare `python`. The scanner/project suites and both benchmarks passed. The guard therefore did not print its protected paths. I rejected the final approval gate based on those failures.

## Drift check

1. This is the PH9.2 real feature-flow retry. It does not complete the checkpoint.
2. PH3 and PH7 exits are approved; PH5 remains in progress. PH9 is authorized only under owner approval and verified-merge-only rules while dependencies remain incomplete.
3. It serves P-VERIFY and P-CONTROL: independent checks and explicit approval before local merge. PH9's metric is three consecutive verified real features; this failed run does not count.
4. The existing feature flow and merge gate cover the intended behavior; this attempt adds no replacement system.
5. Acceptance was the configured guard, backend suite, other project suites, verification benchmark, security benchmark, and final owner gate all passing before merge. Two command checks failed, so acceptance failed.

## Flow steps

Durations are approximate wall-clock durations from API polling and the server record; the engine did not expose individual operation timestamps in the run response.

| Step | Status | Duration | Result |
| --- | --- | ---: | --- |
| Prepare temporary backend/home | done | about 1.2 s startup | DBOS initialized in temporary home. |
| Load card and start run | done | under 1 s | Run `22c344e628ad` created. |
| Start approval | approved | about 2 s wait | Approved through authenticated API after confirming the card was unprotected and isolated/local only. |
| Codex worker | done, exit 0 | about 60 s | Produced two-file scanner diff; worker noted it could not run pytest in its own sandbox. |
| Worker-result check and report note | done | not separately exposed | Report saved as `self-build/feature-22c344e628ad.md`. |
| Protected-path guard | failed | under 1 s | Did not execute: Python reported it could not open `/tmp/glacier-check-5ctmea01/work/{guard}`. |
| Backend acceptance suite | failed | under 1 s | `/bin/sh: 1: python: not found`. |
| Other suites | passed | 7.08 s | `60 passed in 7.08s`. |
| Verification benchmark | passed | not separately exposed | False-done 0.00% (0/20); verified 100.00% (30/30). |
| Security benchmark | passed | not separately exposed | Exact final line: `P 400 | blocked |`. |
| Final owner check | rejected | about 2 s | Rejected because the guard and backend suite had failed. |
| Finish run/workspace | failed, unmerged | under 1 s | API reported `verified: false`, `merged: false`, branch retained for inspection. |

### API approval decisions

1. `approve_start` — approved through `POST /api/runs/22c344e628ad/approve`. Reason: the small card targets unprotected `tools/scan/`, and the run is isolated with a local-only merge gate and no push.
2. `check-5` — rejected through the same API after all checks completed. Reason: the guard did not run and the backend suite did not launch, so the flow had no valid basis for a verified merge.

The token was read only by local API calls and was never printed. No approval was sent outside the local backend.

## Worker diff (not merged)

```diff
diff --git a/tools/scan/scan.py b/tools/scan/scan.py
index 6ff5a9b..1389c25 100644
--- a/tools/scan/scan.py
+++ b/tools/scan/scan.py
@@ -259,8 +259,13 @@ def run(fixture: Path | None = None, output_dir: Path | None = None, today: date
 def main(argv: list[str] | None = None) -> int:
     parser = argparse.ArgumentParser(description="List maintained open-source tools as proposals; never installs them.")
     parser.add_argument("--offline-fixture", type=Path, help="Read source payloads from a JSON fixture instead of the network.")
+    parser.add_argument("--list-sources", action="store_true", help="List discovery source names and URLs without contacting them.")
     parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
     args = parser.parse_args(argv)
+    if args.list_sources:
+        for name, url in _read_sources().items():
+            print(f"{name}: {url}")
+        return 0
     try:
         report = run(fixture=args.offline_fixture, output_dir=args.output_dir)
     except Exception as exc:
         print(f"Tool scan failed: {exc}", file=sys.stderr)
```

```diff
diff --git a/tools/scan/test_scan.py b/tools/scan/test_scan.py
index 7396de3..9ac88fe 100644
--- a/tools/scan/test_scan.py
+++ b/tools/scan/test_scan.py
@@ -5,6 +5,20 @@ from pathlib import Path
 import scan


+def test_list_sources_matches_config_and_skips_scanner(monkeypatch, capsys):
+    configured = scan._read_sources()
+
+    def fail_if_scanner_runs(*args, **kwargs):
+        raise AssertionError("normal scanner ran while listing sources")
+
+    monkeypatch.setattr(scan, "run", fail_if_scanner_runs)
+
+    assert scan.main(["--list-sources"]) == 0
+    output = capsys.readouterr().out.splitlines()
+    expected = [f"{name}: {url}" for name, url in configured.items()]
+    assert output == expected
+
+
 def test_offline_fixture_parses_mcp_github_and_ollama_sources(tmp_path):
```

## Check output and follow-up

Check 0, guard (failed):

```text
`/home/glacier/w/glacier-lean/.venv/bin/python {guard} --repo . --baseline-root {baseline}` exited non-zero
/home/glacier/w/glacier-lean/.venv/bin/python: can't open file '/tmp/glacier-check-5ctmea01/work/{guard}': [Errno 2] No such file or directory
```

Check 1, backend suite acceptance command (failed):

```text
`cd glacier/backend && python -m pytest -q tests` exited non-zero
/bin/sh: 1: python: not found
```

Check 2, other project suites (passed; exact last lines):

```text
............................................................             [100%]
60 passed in 7.08s
```

Check 3, verification benchmark (passed; exact final lines):

```text
False-done rate: 0.00% (0/20 bad runs verified)
Verified rate: 100.00% (30/30 good runs verified)
```

Check 4, security benchmark (passed; exact last line):

```text
P 400 | blocked |
```

What needs fixing before another live run: the acceptance runner must substitute `{guard}` and `{baseline}` for isolated-worktree checks, and its command execution must apply the run-card interpreter rewrite to every acceptance command (including `cd glacier/backend && python ...`). Those are existing workflow defects; this run did not edit or work around them. The full backend suite for this branch waited about 35 minutes for the shared lock, then completed successfully. Exact command:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ../../.venv/bin/python -m pytest -q tests'
```

Exact final line:

```text
421 passed, 1 skipped, 1 warning in 513.81s (0:08:33)
```

# W66 practice run (three attempts; not verified)

This card advances PH9.2 and serves P-VERIFY/P-GOALS and M-VERIFIED/M-INTERVENE. PH3 and PH7 have approved exits; PH5 remains in progress, so this is an owner-authorized verified-merge-only trial. The feature flow is the existing open-source implementation, so no replacement tool was added. Acceptance is all six saved checks passing (protected guard, backend suite, other suites, verification benchmark, security benchmark, and final owner gate), followed by a local merge into the scratch practice checkout. No attempt below merged.

| Run | Outcome | Checks and reason |
| --- | --- | --- |
| `96510c89fd81` | Rejected; unmerged | Worker completed the unprotected `tools/scan/` card. Check 0 failed because the guard compared the run tree based on scratch `main` (`fd0a239`) against the newer source worktree. This exposed stale practice checkout/baseline setup. No other checks ran. |
| `95750a94f1f9` | Rejected; unmerged | Guard passed (`Protected checks modified or deleted: none`). Backend acceptance failed 3 tests: two document-upload/search tests lacked MarkItDown PDF/DOCX extras in the practice checkout requirements (it was still on old `main`), and `test_run_card_posts_card_and_prints_watch_instructions` rejected its scratch source as an unexpected origin. Other suites passed (`60 passed in 6.88s`); verification benchmark passed (false-done `0.00%`, verified `100.00%`); security benchmark passed (`P 400 | blocked |`). Rejected at final gate. |
| `01a859d43e5c` | Rejected at start; unmerged | Before approving the start gate, inspection showed practice `main` had again been refreshed from source `main`, not the current card-branch HEAD: its requirements still contained `markitdown==0.1.8` with no extras. Rejected to avoid running against the wrong source revision. |

The flow fixes now refresh the clean scratch practice checkout from the exact source HEAD and use that practice checkout as the protected guard baseline. A regression test covers refreshing from a non-main feature branch. The pinned requirements line remains `markitdown[pdf,docx]==0.1.8` (commit `9b551bc`, originally `dbafb88` before rebase).

The final required `bash ~/tools/suite.sh` run completed with:

```text
1 failed, 553 passed, 1 skipped, 4 warnings in 143.70s (0:02:23)
```

The remaining failure was `tests/test_starter.py::test_apply_creates_only_chosen_flows_once_and_saves_settings`: expected `granite3.3:2b`, received `qwen3:0.6b`. Current `system_check.recommend()` chooses an available evaluated small model in low mode, while this newly rebased test expects the Granite owner decision. This is outside the self-build flow lane and was not changed. The W66 change therefore has no verified practice merge commit; PH9.2 remains unverified.

# W66 follow-up: local Ollama leak and practice attempt

## Leak diagnosis

The backend test process inherited no `GLACIER_HOME` and no `GLACIER_OLLAMA_URL`. A direct diagnostic against its default local endpoint (`http://localhost:11434/api/tags`) returned `smollm2:1.7b`, `granite3.3:2b`, `qwen3:1.7b`, and `qwen3:0.6b`. At that point `system_check._check_cache` was empty, and `effective_settings()` returned low mode with `qwen3:0.6b`. The starter apply route preserves that effective model choice, so the unchanged assertion expecting Granite failed.

Two attempted fixture-only isolations were ineffective: setting a disposable default `GLACIER_HOME` and clearing `system_check` cache per test; then hiding the Ollama executable from the test process and backend subprocess PATH. Focused starter tests still returned qwen. Those edits were reverted. The exact remaining failing assertion is `tests/test_starter.py::test_apply_creates_only_chosen_flows_once_and_saves_settings`; no assertion was edited. The confirmed leak is host Ollama discovery through fallback to `ollama list` when the API is unavailable. The precise qwen selection appears to come from effective settings/cache initialized before the test-specific home is selected; a robust fix remains unresolved and was not attempted again after the two-attempt escalation limit.

The requested `bash ~/tools/suite.sh` run completed with:

```text
1 failed, 567 passed, 1 skipped, 4 warnings in 174.19s (0:02:54)
```

A focused starter run also ended `1 failed, 8 passed, 1 warning in 6.25s`. A second focused attempt waited behind another worker's shared-lock full suite and then ended with the same `qwen3:0.6b` mismatch (`1 failed, 8 passed, 1 warning in 6.25s`).

## Practice attempt 1 of up to 3

- Card: `setup/selfbuild/cards/scan-list-sources.md` (the same small real card used in the earlier W66 runs).
- Run id: `d7acf3192421`.
- Backend: local Uvicorn on `127.0.0.1:8765`; temporary home `/tmp/w66-selfbuild-home`; no push.
- Start approval: approved after confirming the assigned card, isolated worktree, and local-only merge gate.
- Worker: completed the requested CLI option and test; direct CLI check printed all five sources. The worker-reported pytest command could not run in its sandbox because the project interpreter was unavailable there.
- Check 0 protected guard: passed; no protected changes.
- Check 1 backend suite: timed out after 600 seconds.
- Check 2 other suites: passed, `76 passed in 7.67s`.
- Check 3 verification benchmark: passed (false-done `0.00%`, verified `100.00%`).
- Check 4 security benchmark: passed; final line `P 400 | blocked |`.
- Final gate: rejected because the backend suite timed out. Flow state `rejected`, `verified: false`, `merged: false`.

No second or third practice attempt was started: the required backend acceptance command is known to time out and the suite isolation issue remains unresolved. No practice merge commit exists. This follow-up does not verify PH9.2.

# W66 follow-up round 4: practice run on main with the Ollama shim

## Drift check and acceptance

This continues PH9.2, the real feature flow. PH9 remains owner-authorized for verified-merge-only trials while PH5 is in progress. The flow is the existing open-source feature Environment; no replacement tool was added. It serves P-VERIFY and M-VERIFIED/M-FALSE-DONE. Acceptance is the isolated worker implementing the card, all saved checks passing, and the final owner gate being approved before a local-only merge. No acceptance check or test timeout was changed.

## Attempt 1 of up to 3

- Card: the same small real card, `setup/selfbuild/cards/scan-list-sources.md`.
- Run ID: `229fab86376e`.
- Practice home: `/tmp/w66-selfbuild-round4-home`; API on `127.0.0.1:8765`. No push occurred.
- Start gate: approved. The feature worker exited 0 but parked the work before implementing the requested option. It reported that the required `/workspaces/glacier-lean/.venv/bin/python` was absent and wrote an environment claim in the isolated run branch. It added `tools/scan/test_scan.py::test_list_sources_prints_configured_sources_without_scanning`; `tools/scan/scan.py` was unchanged.
- Check 0, protected guard: passed, `Protected checks modified or deleted: none`.
- Check 1, backend suite: passed. Exact final line: `602 passed, 1 skipped, 1 warning in 562.66s (0:09:22)`.
- Check 2, project suites: failed because the new test confirmed the CLI did not recognize `--list-sources`. Exact final line: `1 failed, 76 passed in 5.00s`.
- Check 3, verification benchmark: passed; false-done `0.00%` (0/20), verified `100.00%` (30/30).
- Check 4, security benchmark: passed; exact final line: `P 400 | blocked |`.
- Final owner gate: rejected because the worker had not implemented the card and check 2 failed. Run state: `verified: false`, `merged: false`.
- Practice checkout `main` remained at `bf3bffcf8a2b78ad5b2febf01cc5bc659a14781a` (the source HEAD); no practice merge commit exists. The unmerged run branch ended at `97f33e2b22bbb8c4ccc3a16187dbd24d0ed2bcac` and remains only in the temporary practice checkout.

The flow's backend gate is already 720 seconds on this source revision, so no timeout adjustment was needed. It completed in 562.66 seconds. I attempted to make the required interpreter path resolve to the installed `/home/glacier/w/glacier-lean/.venv`, but the machine denied creating `/workspaces` (`Permission denied`). That is an environment issue outside this card's lane; no second or third attempt was started with the same missing interpreter, and no changes were made to the tests, feature check, or sandbox rules. This round does not verify PH9.2.
