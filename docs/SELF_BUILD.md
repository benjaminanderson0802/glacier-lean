# Glacier builds Glacier

Glacier's feature flow turns a card file into a normal Glacier run. The owner first approves the start. The Codex worker then works in an isolated Git worktree with the `workspace-write` sandbox. Its changes stay on a run branch while independent checks run.

`setup/selfbuild/run_card.py` first clones or verifies the Glacier checkout at `$GLACIER_HOME/workspaces/self-feature`. The feature flow works in a per-run isolated worktree based on that checkout. Its first required check runs `setup/selfbuild/protected_guard.py` from the main checkout and compares protected files in the run copy with the main checkout. It fails if the worker edits or deletes tests, test configuration, health checks, benchmarks, verification code, or either self-build flow. The guard also prints the list of protected paths for owner review.

The run is merged into the local checkout's main branch only after every required check passes. The merge queue serializes merges and keeps conflicting work available for review. A failed test or failed verification check leaves the work unmerged. The flow never pushes to GitHub. Pushing is a separate action that needs separate approval.

The fixed acceptance checks are ordered: protected-path guard, full backend suite, other project suites, verification benchmark, and security benchmark. The benchmark runner's exit code is the gate, with results written into the run copy. The final owner check says: “Approve only if you reviewed the protected-path list above”.

## Safety rule

I-14 says agents may tighten safety rules but may not loosen them. A worker must not alter its own acceptance checks or weaken project invariants. A proposed change to a safety rule needs a human amendment to `NORTHSTAR.yaml`; this flow does not make that amendment. The verifier reads checks from the saved flow outside the worker's worktree, and the guard itself runs from the main checkout. The isolated worktree reaches local main only after verification succeeds.

## Run a card

Save the card as a text file, then run:

```sh
python setup/selfbuild/run_card.py path/to/card.md
```

`run_card.py` prints the feature run ID and API address to watch. It also installs the `self-maintenance` environment as a convenience, but it starts the feature-card run; it is not the weekly-run command. To run weekly maintenance by itself, install the configured `self-maintenance` graph through `PUT /api/environments/self-maintenance`, start it with `POST /api/environments/self-maintenance/run`, and poll `GET /api/runs/{run_id}`. Configure its command working folders and maintenance script path for the checkout being inspected before saving it.

The weekly flow checks pinned Python packages and npm packages in the web and desktop projects, confirms package licences, and runs the backend tests and screen check. Its `status_note` step saves the result to `proposals/maintenance-YYYY-MM-DD.md` in the vault as `run:<id>`. The proposal includes new tool suggestions from the MCP registry, GitHub topics, and the Ollama library, using the scanner's open-source and recent-activity filters. Each source has a 20 second limit; a source that cannot be reached is marked “could not check right now.” The tool list shows at most 10 entries, and a note over 7,500 characters is shortened by trimming tool suggestions first, then package upgrade suggestions. Suggestions are for owner review only: nothing is installed, added to requirements, or adopted. It never edits requirements, lockfiles, or project code. The owner reviews proposals; approved upgrades are made in a separate feature run and tested again.

## First live run

The first real card run was `ea0a71bb2629` on 2026-10-07. Codex completed the requested two-file change in an isolated worktree, but the acceptance commands could not find `python`, so the protected guard and test commands did not run. The run was rejected at the final human gate and nothing was merged. The requested health-check implementation is also on the guard's protected-path list.

The retry run was `22c344e628ad`. The `tools/scan/` card was not protected and the scanner tests and benchmarks passed, but the guard command kept `{guard}` and `{baseline}` literal, and the backend check still used bare `python`. The run was rejected and nothing was merged. Both run records, including diffs, approvals, timings, and exact check output, are in [the live-run evidence](../evidence/live/selfbuild_first_card.md).

## W66 practice run

W66 exercised the feature flow three times on the `tools/scan/` source-list card. Runs `96510c89fd81`, `95750a94f1f9`, and `01a859d43e5c` were all rejected and none merged. The first exposed a stale practice base in the guard comparison; the second exposed the practice checkout origin mismatch and confirmed the PDF/DOCX extras were absent from its old requirements snapshot; the third was rejected before worker approval because refresh still selected source `main` instead of the exact source HEAD. The flow now refreshes from the exact source commit and uses the practice checkout as the guard baseline. The backend tests for this fix passed (15 passed); the required full suite ended with `1 failed, 553 passed, 1 skipped, 4 warnings in 143.70s (0:02:23)`, due to a separate starter low-mode default mismatch. There is no verified merge commit, so this run does not complete PH9.2. See [detailed run evidence](../evidence/live/selfbuild_first_card.md).

## W66 follow-up: Ollama isolation blocker

The follow-up practice attempt used the same small `tools/scan/` card as the earlier W66 runs. Run `d7acf3192421` passed its protected guard, other project checks (`76 passed in 7.67s`), verification benchmark (false-done `0.00%`, verified `100.00%`) and security benchmark (`P 400 | blocked |`). Its backend acceptance check timed out after 600 seconds, so the final gate was rejected and there is no verified merge commit.

The laptop leak is the real local Ollama service: its model list included qwen models, and recommendation/settings discovery selected `qwen3:0.6b` where the unchanged starter acceptance test expects `granite3.3:2b`. The required suite ended `1 failed, 567 passed, 1 skipped, 4 warnings in 174.19s (0:02:54)`. Two attempted fixture isolations were ineffective and reverted; the test assertion was not changed. The remaining fix needs to isolate model discovery before the backend process/cache initializes. No additional practice runs were started because this known suite failure prevents verified merge. Full run details and exact diagnostics are in [the live-run evidence](../evidence/live/selfbuild_first_card.md).

## W66 follow-up round 4

Main now includes the test-only Ollama shim (PR #125), along with the reliability and speed updates in PRs #131, #119, and #133. The next same-card practice run was `229fab86376e`. Its backend gate passed (`602 passed, 1 skipped, 1 warning in 562.66s (0:09:22)`), but the worker parked because `/workspaces/glacier-lean/.venv/bin/python` was missing in its worktree. It added a test without implementing `--list-sources`; the project suite caught that (`1 failed, 76 passed in 5.00s`). The protected guard and both benchmarks passed, but the final gate was rejected. No practice merge was made; practice `main` stayed at `bf3bffcf8a2b78ad5b2febf01cc5bc659a14781a`.

The practice gate is already set to 720 seconds, and this backend run finished within that limit, so no timeout was changed. The worker stopped because its project instructions required the unavailable `/workspaces/glacier-lean/.venv/bin/python`; the run log confirms it had start approval and workspace-write access, and independent check 2 caught the unimplemented option (`1 failed, 76 passed in 5.00s`). Commit `6a8ed33` makes generated acceptance commands use `GLACIER_PYTHON` or `sys.executable`, removes the old fixed path from runtime scripts and bench instructions, and strengthens the worker handoff with the whole card, acceptance requirements, explicit practice-worktree edit authorization, and a claim requirement for questions/blockers. The generated-command and handoff regression tests were waiting on the shared test lock. No new run was started pending those tests, so there is no verified run or practice merge commit in this round. See the [run evidence](../evidence/live/selfbuild_first_card.md).

## W66 follow-up round 6

The same source-list card ran three more times: `617614d66236`, `ca0e17832d79`, and `41ff928d74e8`. Each worker completed, the protected guard passed, the project checks passed (`77 passed`), and both benchmarks passed (false-done `0.00%`, verified `100.00%`; security `P 400 | blocked |`). The backend suite failed the same three tests each time: `test_send_get_completes_with_output_and_author`, `test_codex_prev_output_substitution`, and `test_codex_streams_live_log_while_running`. The two retry suites ran under the shared lock and still ended with `3 failed, 602 passed, 1 skipped, 1 warning` (in 471.09s and 457.42s). A focused rerun of those three cases passed, but the suite-level cause is unresolved. The final gate was rejected on each run; all are unverified and unmerged.

After the first rejection, the feature flow's backend command was changed to acquire the shared suite lock. This did not resolve the failures, and no checks were changed or skipped. The practice checkout remains at `e527f5a4169170e4e2423ee8c29a2294f88444b1`, the flow-fix source base; there is no feature merge commit. No different cards were started because none of these runs verified. PH9.2 remains unverified. See the [run evidence](../evidence/live/selfbuild_first_card.md).

## W95 practice verification

The W66 practice database was still available at `/tmp/glacier-w66-round6-home/glacier.sqlite`. Its saved records confirm the same three failures in all three runs: `test_send_get_completes_with_output_and_author`, `test_codex_prev_output_substitution`, and `test_codex_streams_live_log_while_running`. The independent-check output retained only abbreviated pytest assertion lines (`As...`, `AssertionErr...`, `assert...`), so it does not preserve the failed values or a traceback. The test code and fake Codex executable in the saved practice checkout match this branch; `fake_codex.py` is tracked executable, and the fixtures set `CODEX_BIN` directly. A focused rerun and a fresh-clone full backend suite both passed. That rules out a stable failure in the current checkout, but does not establish what caused the historical assertions; no test or acceptance check was changed.

W95 live run `bafcca9a56d9` passed its protected guard, project suites and benchmarks, but its backend check timed out after 600 seconds while queued for the shared lock. It was rejected and did not merge. Run `3de97e6b0756` then passed the complete suite inside the verifier's temporary copy (`605 passed, 1 skipped, 1 warning in 446.19s`), project checks (`77 passed`), verification benchmark (false-done `0.00%`, verified `100.00%`), and security benchmark (`P 400 | blocked |`). After review of the protected-path result, the final owner check was approved. The feature commit `85807ac` merged locally as `9cdd84d`; no push occurred. This supplies one verified PH9.2 feature run, not the three consecutive runs needed for the PH9 exit. Full diagnostics and run records are in [the live evidence](../evidence/live/selfbuild_first_card.md).
