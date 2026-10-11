# E-PH3 verification results

## Follow-up: protected-file provenance

This follow-up adds a durable workflow step that snapshots each protected acceptance file after workspace preparation and before workflow nodes run. The verifier compares the final workspace with that baseline before restoring trusted check content. The local diagnostic in `protected-provenance-diagnostic.json` rejects deletion, modification, and creation after the snapshot, and accepts a verifier-only check file that was absent both before and after work. It is builder evidence, not independent acceptance.

PH3.2 remains in progress. The tester-owned independent adversarial cases and a green backend board are still required; the two filed claims remain open. No benchmark metric has been remeasured by this change.

## Earlier validation attempts

Implementation: `f644fbf` (`verify.py` only). Protected check files are inspected in the verifier's private copy before any restoration. Symlink/reparse and wrong-file-type paths are refused; modified content fails without writing; saved check file paths/content are validated. No acceptance test, benchmark case, contract, or screen behavior was changed.

## Evidence boundaries

- `before-symlink.json`: direct-call reproduction on the original code, which rejected modified content but overwrote an outside file through a worker symlink.
- `after-protected-files.json`: builder diagnostics for file, directory and dangling symlinks, content edits, unchanged content and verifier-only absent files. Unsafe paths reject; outside content stays intact; unchanged/absent saved checks pass. These are **not independent acceptance tests**, and Windows reparse handling was not tested live.
- Existing backend tests spawn real uvicorn/DBOS servers. Their model/specialist workers use fixtures, not real model judgment.
- The live Codex script used the real subscription CLI against an owned authenticated backend, but the run failed (`database is locked`). The script's zero exit and LIVE_DONE do **not** count as success.
- The attempted manual symlink API diagnostic was interrupted by the owned live backend's shutdown; no completed API result is claimed.

## Commands and outcomes

All Python commands use `~/w/glacier-lean/.venv/bin/python`.

- Backend scoped run from `glacier/backend`: `-m pytest -q tests/test_verification.py tests/test_workspaces.py tests/test_claims_proof.py tests/test_claims_specialist.py tests/test_claims_research.py tests/test_claims_guard.py tests/test_claim_rerun.py tests/test_claims_capability_routing.py` — **33 passed, 4 failed, 1 setup error** in 1056.15 seconds; full output in `targeted-tests.log` (trailing whitespace trimmed for git).
- `-m pytest -q bench/verification/test_validate.py bench/verification/test_run_glacier.py bench/claims/test_claims_cases.py bench/claims/test_claims_runner.py` — **12 passed**, 58.13 seconds. Fixture/case/runner coverage only; not live benchmark metrics.
- `bench/verification/run_glacier.py --results evidence/E-PH3/verification-benchmark.md` — **incomplete**, backend not ready within the existing 45-second limit; no new M-FALSE-DONE/M-VERIFIED values.
- `bench/claims/run_claims.py --results evidence/E-PH3/claims-benchmark.md` — **incomplete**, API write timed out; no new claim-resolution metrics.
- `bash setup/live_codex_check.sh` — real backend run `2fbfb4512fba` **failed**, worker database locked, downstream steps skipped; script itself exits 0.
- Full backend suite requested under `flock /tmp/glacier-suite.lock` — **not run**, parked after 9+ minutes queued, before pytest started. Only this card's childless lock waiter was cancelled.
- From `glacier/web`, `npx tsc -b` — **blocked**, shared node_modules has no project TypeScript compiler.
- `node e2e/theme_lint.mjs` — **passed**, 52 files.
- `node scripts/check-i18n.mjs --fail` — **blocked**, ERR_MODULE_NOT_FOUND for typescript.
- `git diff --check` and Python parse/compile of `verify.py` — **passed**.

The literal core board script was inspected, not run: it installs into shared venv/node_modules, deletes fixed `/tmp/e2edata`, and starts an unowned fixed-port backend. Its safe checks were run individually as above. Browser build/e2e is blocked by the existing dependency gap; no screen changes were made.

## Scoped failure details

- `test_worker_cannot_weaken_the_check`, `test_rubric_check_uses_separate_judge`, and `test_gap_with_free_option_goes_to_fixer_with_findings`: backend startup exceeded the unchanged fixture deadline; captured server logs were empty.
- `test_runs_merge_one_after_another`: HTTP read timeout during a run request.
- `test_tampering_fails_even_when_the_work_is_right`: the verifier **recorded the expected failed protected-content check**, but the run stayed `running` past the test's completion deadline, so the test failed. A recorded rejected check is not enough to call the full runtime case passing.

High shared-host load was observed, but the cause of every timeout has not been independently established. No timeout/assertion was changed and no repeat attempt was made. These failures require the environment/runtime lane; this card does not claim a green suite.

## Still open

PH3.2 is reopened rather than falsely claiming complete I-04 enforcement. Independent adversarial coverage and pre-work provenance for deleted checks remain pending `CLM-2026-10-10-E-PH3-INDEPENDENT-PROTECTION`. Shared-environment validation is parked under `CLM-2026-10-10-E-PH3-VALIDATION-ENVIRONMENT`. Existing owner exit decisions and historical benchmark figures are not changed, and no new checkpoint or phase is marked done.
