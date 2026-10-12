# C-PH5-PLAN-FIDELITY-TESTER — Ensure planning uses the exact reviewed goal and checks

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `reviewed-plan-evaluator`. Allowed edits: new `tests/backlog/test_C_reviewed_plan_fidelity.py` and `evidence/backlog2/C-PH5-PLAN-FIDELITY-TESTER/`. Do not edit planner/UI/API product code or existing tests.

## Goal

Independently exercise the reviewed-plan path described in `CLM-2026-10-10-E-PH5-SPEC-EDITS`: edit the proposed goal and acceptance checks, approve them, and verify the generated plan references that exact reviewed version. Reject silent replacement by original draft or model-generated checks.

Read first: the claim, `docs/CONTRACT.md`, `glacier/backend/tests/` planning checks, `glacier/web/e2e/` relevant Build spec, `NORTHSTAR.yaml` PH5.2.

## Drift check

- Checkpoint: PH5.2. PH3/PH4 feed PH5; PH3 exit is owner-approved, PH4 checkpoints are built, PH5 remains in progress.
- Properties/metrics: P-GOALS, P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current build API and e2e harness; no new planner.
- Acceptance first: reviewed goal/spec bytes and check identities survive approval and planning, and are visible before any run; reject/edit paths remain intact.

## Verification

Run the independent API/UI check with the current mock and real backend in an isolated home. Preserve existing test IDs and behavior; return failing evidence to a separate builder.
