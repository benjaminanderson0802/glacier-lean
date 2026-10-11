---
id: CLM-2026-10-10-U-VENTURES-VERIFICATION
filed_by: U-VENTURES
run_id: null
node_id: null
checkpoint: PH12.1
kind: environment
summary: Venture verification encountered shared dependencies, backend contention, stale UI expectations, and Git object-store corruption
evidence: evidence/U-VENTURES/verification.md
attempts_made: 1
status: filed
assigned_to: integrator / independent tester
resolution: null
resolution_evidence: null
---

Initial focused backend run: 9 passed, 1 failed, 1 setup error in 254.59 s.
The engine startup exceeded the existing 60 s timeout at DBOS initialization;
the every-second schedule acceptance case failed with `sqlite3.OperationalError:
database is locked` in runner.snapshot_scheduled_run / store.create_run. These
runtime paths are outside this UI card and were not edited.

The supplied node_modules symlink targets an empty shared directory. Reused the
isolated lockfile installation workaround recorded in
2026-10-08-w89-ui-dependencies.md; no shared dependency directory is modified.

The existing tester-owned e2e/ventures.spec.mjs expects setting-up/running status,
pause/resume and editable steps on venture cards. The current owner card instead
requires live/ready/blocked and read-only content plus run now. Preserve the old
check for independent tester revision; do not change assertions to pass this work.

Additional environment finding on 2026-10-10: this card branch is 12 commits behind
`origin/glacier-final`. Inspecting the divergence reported empty shared Git object
files `cf85d3ede3097fc0714fd25e9c38d64f4f07d6bc` and
`47c94d4db98e74e874124a5e6c5095b634430ef0`. No rebase was attempted while the
object store is damaged; the integrator should repair/verify the shared checkout
and replay this card commit on the current base.
