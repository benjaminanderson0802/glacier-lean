# C-PH5-SUPERVISOR-TESTER — Independently verify evidence-aware team supervision

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `team-supervisor-evaluator`. Allowed edits: new focused test under `glacier/backend/tests/` named with `C-PH5-SUPERVISOR` and `evidence/backlog2/C-PH5-SUPERVISOR-TESTER/`. The supervisor implementation, prompts and existing checks are read-only.

## Goal

Reproduce `CLM-2026-10-11-E-PH5-LIVE-REVIEW` with a deterministic passing command check and a separate reviewer route. Verify the supervisor consumes check evidence correctly, does not contradict a passing exact-byte check without a reason, and still blocks when evidence is missing or fails.

Read first: the claim, `evidence/E-PH5/live-runtime-v2-final.json`, `docs/contracts/VERIFICATION.md`, `NORTHSTAR.yaml` PH5.3.

## Drift check

- Checkpoint: PH5.3. PH5 remains in progress; this checks the approval/verification contract without asserting phase exit.
- Properties/metrics: P-VERIFY, P-CONTROL; M-FALSE-DONE, M-VERIFIED.
- Existing tools: current supervisor, deterministic check and existing test harness; no new reviewer service.
- Acceptance first: passing evidence is accepted with a traceable reason; absent, contradictory or failing evidence never becomes approved completion.

## Verification

Run the new focused backend test and relevant supervisor tests. Keep the exact task/check unchanged; if reviewer behavior remains ambiguous, file a claim rather than relax the evidence rule.
