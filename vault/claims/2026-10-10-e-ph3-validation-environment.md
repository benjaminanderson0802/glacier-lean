---
id: CLM-2026-10-10-E-PH3-VALIDATION-ENVIRONMENT
filed_by: worker:E-PH3
run_id: ''
node_id: ''
checkpoint: PH3.4
kind: environment
summary: PH3 revalidation is limited by shared dependency gaps and backend startup/API timeouts
evidence: evidence/E-PH3/verification-benchmark.log; evidence/E-PH3/claims-benchmark.log; evidence/E-PH3/verification-benchmark-followup.log; evidence/E-PH3/claims-benchmark-followup.md; evidence/E-PH3/backend-full-followup.log; evidence/E-PH3/targeted-followup.log; evidence/E-PH3/typescript.log; evidence/E-PH3/i18n.log
attempts_made: 0
status: filed
assigned_to: fixer
resolution: ''
resolution_evidence: ''
---

## Problem

The new independent verification benchmark attempt exceeded its existing 45-second startup limit. The claims benchmark started a real backend but an API write exceeded its existing eight-second timeout. The shared machine reported a load average of 29 during concurrent card tests. These are environment observations, not a proven verifier regression or a passing phase result.

The worktree's pre-existing node_modules symlink points to the shared checkout, where TypeScript is unavailable: `npx tsc -b` does not find the project compiler and `node scripts/check-i18n.mjs --fail` raises ERR_MODULE_NOT_FOUND for typescript. `node e2e/theme_lint.mjs` passes.

## Research

The same dependency gap and unsafe legacy board behavior were recorded in `2026-10-10-a-apify3-shared-validation.md` and its linked earlier claim. Use the fixer's isolated frontend install of the existing lockfile; do not install or mutate shared dependencies from this verification card. Serialize backend benchmarks when the host has capacity, preserving the tester-owned limits and assertions.

`setup/run_core_tests.sh` mutates the shared venv/node_modules and deletes fixed `/tmp/e2edata`; running it literally would conflict with shared-worker isolation. Non-mutating board portions are run individually. The full backend suite is started under `/tmp/glacier-suite.lock`; final outcomes belong in `evidence/E-PH3/RESULTS.md`.

## Resolution

Pending a green full board and benchmark remeasurement in a healthy isolated environment. No test, timeout, assertion, package pin, or shared process was changed to obtain a pass.

## Live worker outcome

The unmodified `setup/live_codex_check.sh` ran against an owned disposable real backend, with install-token authentication supplied through a temporary curl config. It started run `2fbfb4512fba`; the worker failed with `database is locked`, and downstream steps were skipped. The script itself returned zero and printed LIVE_DONE. This is failed live evidence, not a successful Codex proof. Backend startup/shutdown and the request path are recorded in `live-backend.log`; only the backend process started by this card was stopped.

An additional manual symlink API diagnostic was interrupted when that owned backend shut down after the live script; it has no completed result and is not counted as proof. The direct-call diagnostic remains the only completed new symlink reproduction.

## Full-board queue

After more than nine minutes waiting for the shared suite lock, the full-suite request was parked. The cancelled process was only this card's childless `flock` waiter; pytest had not started. The separately started scoped PH3 suite continues to completion. No other worker's test or lock holder was touched.

## Scoped suite final outcome

The suite completed normally: **33 passed, 4 failed, 1 setup error in 1056.15 seconds**. Three cases could not start their backend within the fixture deadline; one merge case hit an HTTP read timeout; one tampering case recorded the correct failed verification evidence but its run stayed running past the completion deadline. See `evidence/E-PH3/targeted-tests.log` and `RESULTS.md` for test names. Shared-host load reached roughly 59; load is an observation, not proof of the cause of every failure. The test limits and assertions are unchanged. The existing benchmark fixture suite separately passed 12/12; that is not a live phase metric or a green backend suite.

## Follow-up outcome

The PH3-focused verification/workspace/claims-proof suite passed **19 tests** (`evidence/E-PH3/targeted-followup.log`). A serialized full backend run completed with **826 passed, 1 skipped, 6 failures**; the failures are outside PH3 and are separately filed. The verification live benchmark timed out. The claims live benchmark completed with a 17% resolution figure, but its runner samples routed cases before specialist proof completes; see `CLM-2026-10-11-E-PH3-CLAIMS-BENCHMARK-SAMPLING`. Neither benchmark provides a valid PH3 metric remeasurement. The environment/validation claim remains open.
