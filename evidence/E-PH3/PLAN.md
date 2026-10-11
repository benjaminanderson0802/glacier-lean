# E-PH3 drift check and validation plan

Owner authorization: Benjamin Anderson, 2026-10-10, maximize progress on PH3 only; commit, never push.

1. Checkpoints: PH3.2 independent-check enforcement; remeasure PH3.4 false-done benchmark and PH3.6–PH3.8 claims paths.
2. Dependencies: PH2 remains in_progress. The assigned card permits work now; it does not authorize declaring the PH2 exit. PH3 has an existing owner-approved exit_decision, but its phase status remains in_progress.
3. Properties and metrics: P-VERIFY and P-CONTROL; M-FALSE-DONE, M-VERIFIED, and claim false-fixed evidence.
4. Existing tools: retain the existing Python verifier, git vault, DBOS runtime, pytest suites, and independently authored benchmark runners. The change is path-validation glue using the Python standard library, with no new dependency, service, or paid route.
5. Acceptance defined before implementation: existing `tests/test_verification.py` (especially `test_worker_cannot_weaken_the_check` and `test_tampering_fails_even_when_the_work_is_right`), workspaces/claims suites, and `bench/verification/run_glacier.py` / `bench/claims/run_claims.py`. These files remain untouched. The new symlink attack needs independent tester coverage; manual reproduction artifacts are diagnostic evidence, not independent acceptance.

## Reproduced assumption and first implementation attempt

Assumption: `copytree(..., symlinks=True)` preserves worker-controlled links; restoring protected content through those links can write outside the verifier copy. `before-symlink.json` confirms that the check returned false but overwrote an outside file. The first implementation validates portable relative paths, inspects copied paths without following links, rejects non-regular protected paths, compares copied content, and defers all restoration until every protected file is inspected.

## File lane

Production edits are limited to `glacier/backend/verify.py`. Supporting evidence lives in `evidence/E-PH3/`; unresolved verification/environment work becomes claims in `vault/claims/`. Any NORTHSTAR edits are restricted to PH3 status/evidence; no contract, acceptance, benchmark or existing test file is edited. No screen behavior or API shape changes, so the mock needs no changes.

## Board execution constraints

`setup/run_core_tests.sh` installs into this worktree's shared venv/node_modules symlinks, deletes the fixed `/tmp/e2edata`, and binds port 8000 without ownership checks. Do not run it against other workers' resources. Run its non-mutating backend/type/theme/i18n portions separately and record unavailable browser/dependency steps. `setup/live_codex_check.sh` needs authentication supplied externally and an owned disposable backend on its fixed port; run unchanged if that port is available. No owner decisions, paid APIs, publication or push.
