# E-PH1 — 2026-10-10

Owner authorization: Benjamin Anderson's E-PH1 card, maximize backend PH1 progress;
commit only, no push, no paid services, no owner-only actions.

## Drift check and acceptance before implementation

1. Advance PH1.2 (scheduled runs), PH1.4 (child flows), PH1.5 (retries),
   and PH1's M-AUDIT exit requirement.
2. PH0 is marked done in NORTHSTAR. This card explicitly authorizes starting;
   no dependency or phase status is changed on that basis alone.
3. P-LOOPS and P-CONTROL; M-SURVIVE and M-AUDIT.
4. Reuse pinned DBOS, SQLite, git and the existing audit recorder. Only Glacier
   event placement needs fixing; no new engine, dependency or paid service.
5. Existing independent checks: tests/test_core.py,
   tests/test_audit_coverage.py, tests/test_audit_log_resilience.py,
   tests/test_reliable_schedules.py, tests/test_schedule_removed.py.
   Run these unchanged and the full backend suite. Add ordinary unit regression
   tests before edits: each command attempt has an audit row, one child start
   has one row, and a successful schedule reservation has a start row while a
   refused reservation does not. These added tests are builder regressions,
   not independent acceptance or proof of the whole phase exit.

## PH1 exit inventory at task start

Exit: PH1.1–PH1.7 done; M-AUDIT = 100% for runtime side effects.
All seven checkpoints are already marked done with historical evidence:

- PH1.1: environment files and one git commit per save.
- PH1.2: core node types, crash recovery, schedules, restart-safe approvals.
- PH1.3: live canvas, edits, node states, terminal, approvals, history, vault.
- PH1.4: bounded loops and nested environments.
- PH1.5: retries, timeouts, one failure alert.
- PH1.6: shutdown within five seconds with live clients.
- PH1.7: Windows core; owner-PC result recorded for 2026-10-08.

No checkpoint is labeled unverified, but this checkout has not yet been
revalidated. The overall phase remains in progress without phase-exit evidence.
This Linux backend card cannot renew owner-PC or screen acceptance. Runtime
audit completeness needs renewed measurement; historical recovery benchmarks
cover a subset of side effects, not all runtime paths.

## Reproduced / suspected gaps before implementation

Source inspection found two identical child-start writes, command audit writes
after the retry loop (only the last outcome), and no start audit in the schedule
snapshot step. Reproduce via the unit regressions before editing the runner.
Assumptions: command attempts may each cause effects even when they fail;
an unchanged event type with added attempt metadata preserves consumers;
DBOS remains responsible for replay of completed steps.
