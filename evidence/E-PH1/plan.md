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

## PH1 exit inventory and current verification boundary

Exit: PH1.1–PH1.7 done; M-AUDIT = 100% for runtime side effects.
NORTHSTAR currently marks all seven checkpoints done with linked historical
evidence, but this Linux backend card does not renew the UI or Windows checks.
The checkpoint evidence on record is:

- PH1.1: environment files and one git commit per save.
- PH1.2: core node types, crash recovery, schedules, restart-safe approvals.
- PH1.3: live canvas, edits, node states, terminal, approvals, history, vault.
- PH1.4: bounded loops and nested environments.
- PH1.5: retries, timeouts, one failure alert.
- PH1.6: shutdown within five seconds with live clients.
- PH1.7: Windows core; owner-PC result recorded for 2026-10-08.

The backend checkpoints not revalidated before this card's work are PH1.1
(vault save + git commit), PH1.2 (durable runs/schedules/restart approvals),
PH1.4 (bounded loops/sub-environments), PH1.5 (retry/timeout/alert policy),
and PH1.6 (shutdown with live clients). PH1.3's live canvas and PH1.7's Windows
core are outside this backend lane and remain supported only by their linked
historical screen and owner-PC evidence. The focused tests below revalidate
audit coverage and schedules, plus several core paths; they do not re-prove each
checkpoint acceptance contract. PH1 remains in progress because the phase exit
still requires current evidence that M-AUDIT is 100% across runtime side effects.
The historical 66/66 recovery audit covers selected effects, not all runtime
paths, and cannot close that gate.

## Reproduced / suspected gaps before implementation

Source inspection found two identical child-start writes, command audit writes
after the retry loop (only the last outcome), and no start audit in the schedule
snapshot step. Reproduce via the unit regressions before editing the runner.
Assumptions: command attempts may each cause effects even when they fail;
an unchanged event type with added attempt metadata preserves consumers;
DBOS remains responsible for replay of completed steps.

## Verification outcome

- Focused backend run:
  `~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_runtime_effect_records.py tests/test_audit_coverage.py tests/test_audit_log_resilience.py tests/test_reliable_schedules.py tests/test_schedule_removed.py tests/test_core.py`
  — 59 passed, 1 warning, 122.80s. The `Server` fixture starts the real
  FastAPI/uvicorn backend with DBOS and isolated temporary homes; checks are not
  mock-server-only.
- Full backend suite: not run. Its fresh request waited 15 minutes for the
  shared suite lock and was stopped before a pytest child started. See
  `backend-full.log` and CLM-2026-10-10-E-PH1-BACKEND-VERIFICATION-LOAD.
- The interrupted standalone live probe did not reach the API. No dedicated
  manual live walkthrough or browser run was completed in this backend lane.
- No PH1 checkpoint status changed. PH1 remains `in_progress` because M-AUDIT
  still lacks independent all-runtime-path evidence for its 100% exit gate.
