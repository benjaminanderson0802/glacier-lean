---
id: CLM-2026-10-10-E-PH4-VERIFICATION-ENVIRONMENT
filed_by: E-PH4
run_id: null
node_id: null
checkpoint: PH4
kind: environment
summary: Shared sandbox load and missing shared web dependencies block a clean PH4 test board
evidence: evidence/E-PH4/memory-baseline.log; evidence/E-PH4/typescript.log; evidence/E-PH4/i18n.log; evidence/E-PH4/backend-full-final.log; evidence/E-PH4/memory-final.log
attempts_made: 1
status: filed
assigned_to: fixer
resolution: null
resolution_evidence: null
---

The PH4 baseline test batch starts isolated real backends. Several fixtures failed
to start while the shared host load climbed above 50 (2026-10-10 22:30 UTC).
The batch is allowed to finish; no unrelated process was stopped and no test
timeout or acceptance assertion was changed.

`npx tsc -b` could not find the project's TypeScript compiler, and
`node scripts/check-i18n.mjs --fail` failed with `ERR_MODULE_NOT_FOUND` for
`typescript`. `node_modules` is a preexisting symlink to
`/home/glacier/w/glacier-lean/glacier/web/node_modules`; the expected
`typescript/package.json` is absent. Theme lint passes.

Prior vault research found the same dependency issue in
`2026-10-08-w89-ui-dependencies.md`, and shared-test contention in
`2026-10-10-ph12-22-heavy-test-lock.md`. The known remedy is an isolated pinned
dependency install and coordinated test scheduling, routed to the environment
owner. No new tooling or paid capability is needed.

The old `setup/run_core_tests.sh` removes a fixed `/tmp/e2edata` and installs
dependencies into that shared target. Its fixed-port live backend and the
unauthenticated `setup/live_codex_check.sh` are not suitable to run concurrently
with other cards. The integrator should run the underlying checks in isolation.

After the E-PH4 fixes, the focused final memory acceptance batch passed (61/61,
including the full reinstall proof). The full backend suite completed with
829 passed, 1 skipped, and 8 failures in 1424.95 seconds. The failures were in
assistant run-history, server startup, template/model integration, and Home
counts/order cases; none were in the focused PH4 batch. Full output is recorded
in `evidence/E-PH4/backend-full-final.log`; this claim does not classify or
resolve those out-of-lane failures.

E-PH4 leaves acceptance checks and scripts untouched, and does not close PH4
based on builder-authored unit tests.
