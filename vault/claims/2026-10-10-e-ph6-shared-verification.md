---
id: CLM-2026-10-10-E-PH6-SHARED-VERIFICATION
filed_by: E-PH6
run_id: null
node_id: null
checkpoint: PH6.3
kind: environment
summary: Shared backend startup timed out and shared web dependencies are missing
evidence: "evidence/E-PH6/baseline-tests.log; evidence/E-PH6/typescript.log"
attempts_made: 0
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

Before implementation, the unchanged PH6 checks produced 69 passes and one
fixture setup error: the real backend did not finish starting within the existing
60-second deadline (DBOS initialization was its last log line). No assertion
failed. Other cards were running concurrently; subsequent verification is queued
under the documented /tmp/glacier-suite.lock. No test or timeout was modified.

The worktree's untracked glacier/web/node_modules symlink targets the shared
/home/glacier/w/glacier-lean/glacier/web/node_modules. Its TypeScript executable
was absent when the required npx tsc -b command ran. Dependency installation or
repair belongs to the environment lane, not this card. No dependency was changed.
The required i18n checker and build also fail for missing TypeScript; both
relevant browser specs fail to load missing Playwright. Theme lint passes.
Live PNG upload works, but real OCR cannot run because Tesseract is absent;
Glacier correctly returns the optional installation hint. Existing OCR tests
exercise a stand-in executable and are not live OCR proof.

The legacy setup/run_core_tests.sh also runs npm ci on that shared directory,
removes a fixed /tmp/e2edata folder, and starts an unowned fixed-port backend.
The live_codex_check.sh assumes that fixed port and omits authentication. Running
these scripts verbatim would collide with parallel workers or fail authentication.
Use the documented locked backend suite and isolated real-backend browser checks
until the setup owner supplies concurrency-safe scripts. E-PH6 will preserve the
actual outcomes and will not mark a phase exit on incomplete verification.
