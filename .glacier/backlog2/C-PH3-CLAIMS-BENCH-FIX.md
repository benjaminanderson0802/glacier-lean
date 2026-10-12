# C-PH3-CLAIMS-BENCH-FIX — Wait for specialist proof before recording claim metrics

Owner: Benjamin. Role: **BUILDER only**. Start after C-PH3-CLAIMS-BENCH-TESTER freezes its independent check.

## Scope

Exclusive lane: `claims-benchmark-runner`. Allowed product edit: `bench/claims/run_claims.py`; ordinary runner tests only in a new card-specific file. C-PH3-CLAIMS-BENCH-TESTER's check and all existing judging tests are read-only. Do not change claim-resolution behavior.

## Goal

Correct the benchmark polling/reporting sequence so a routed claim is followed through specialist work and its original-flow proof before the case is scored. Retain timeout and terminal failure accounting; do not inflate the success rate by changing cases or denominator.

Read first: claim `2026-10-11-e-ph3-claims-benchmark-sampling.md`, the tester card, `bench/claims/run_claims.py`, `bench/claims/test_claims_runner.py`.

## Drift check

- Checkpoint: PH3.4. PH3 exit was owner-approved, but PH3.2 and valid fresh benchmark evidence remain incomplete.
- Properties/metrics: P-VERIFY; M-FALSE-DONE, M-VERIFIED.
- Existing tools: existing claim workflow and benchmark harness; no new tool.
- Acceptance first: the independent tester's routed-claim check passes, every resolution has proof, and unchanged benchmark cases report a terminal result.

## Verification

Reproduce the baseline; run `~/w/glacier-lean/.venv/bin/python -m pytest -q bench/claims` and then the claims benchmark only in an isolated real backend. Record the complete outcome; do not edit the evaluator's test or claim PH3 complete.
