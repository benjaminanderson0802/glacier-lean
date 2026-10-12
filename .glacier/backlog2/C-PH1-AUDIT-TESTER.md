# C-PH1-AUDIT-TESTER — Independently test audit events across side-effect boundaries

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `runtime-audit-evaluator`. Allowed edits: new `glacier/backend/tests/test_C_runtime_audit_boundaries.py` and `evidence/backlog2/C-PH1-AUDIT-TESTER/`. Do not edit audit recorder, runner, existing tests or the shared event contract.

## Goal

Close the PH1 exit evidence gap for M-AUDIT by exercising command side-effect start, success, failure, retry, and interruption boundaries, plus unavailable audit storage. Use a fake local command that writes only inside a temporary directory. Require a durable correlated audit record for every attempted effect and an explicit outcome where known; never count a lost log as success.

Read first: claim `2026-10-10-e-ph1-audit-exit-proof.md`, `glacier/backend/audit_log.py`, `glacier/backend/tests/test_audit_log_resilience.py`, `NORTHSTAR.yaml` PH1 exit and `docs/AUDIT.md`.

## Drift check

- Checkpoint: PH1 exit. PH0 is done; PH1 remains in progress because its exit requires M-AUDIT = 100%.
- Properties/metrics: P-CONTROL, P-VERIFY; M-AUDIT, M-RECOVER.
- Existing tools: current event log, DBOS durable steps, SQLite and pytest; no new audit system.
- Acceptance first: each simulated side effect has a correlated start record and known outcome or explicit interrupted/unknown state; storage failure is visible and cannot be reported as fully audited success.

## Verification

Run the new independent tests and existing audit resilience tests with the project interpreter. If event semantics require a contract change or a side effect cannot be observed safely, stop and file a claim; do not change the shared API or alter existing checks.
