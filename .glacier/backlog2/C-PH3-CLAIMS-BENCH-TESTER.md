# C-PH3-CLAIMS-BENCH-TESTER — Freeze a check for terminal claim-benchmark outcomes

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `claims-benchmark-evaluator`. Allowed edits: new `bench/claims/test_C_terminal_outcome.py` and `evidence/backlog2/C-PH3-CLAIMS-BENCH-TESTER/`. The existing runner, its existing tests and the claims workflow are read-only.

## Goal

Create an independent regression check proving the benchmark does not sample a routed claim until its specialist proof run reaches an evidenced terminal state. Cover resolved, proposed and still-running cases without changing the existing denominator or evidence rules.

Read first: claim `2026-10-11-e-ph3-claims-benchmark-sampling.md`, `bench/claims/run_claims.py`, `glacier/backend/claims_research.py`, `glacier/backend/claims_specialist.py`, `NORTHSTAR.yaml` PH3.4.

## Drift check

- Checkpoint: PH3.4. PH3's exit has owner approval, but PH3.2 remains in progress and PH3.4 lacks a valid new metric remeasurement.
- Properties/metrics: P-VERIFY; M-FALSE-DONE, M-VERIFIED.
- Existing tools: current benchmark and pytest; no custom benchmark framework.
- Acceptance first: a simulated routed claim is not scored before the specialist proof completes; terminal status alone without linked proof cannot count as resolved.

## Verification

Run the new check and `~/w/glacier-lean/.venv/bin/python -m pytest -q bench/claims`. Do not edit the judging runner or claim evidence requirements; hand the frozen failing case to a separate builder.
