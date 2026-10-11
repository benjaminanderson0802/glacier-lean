# C-PH8-CLEAN-STARTUP-TESTER — Check desktop startup without developer Git

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `desktop-no-git-evaluator`. Allowed edits: new independent test under `desktop/` named with `C-PH8-CLEAN-STARTUP` and `evidence/backlog2/C-PH8-CLEAN-STARTUP-TESTER/`. No packaging or vault code, signing workflow or existing test edits.

## Goal

Independently reproduce the installer startup gap in `CLM-2026-10-10-E-PH8-GIT-PREREQUISITE` with developer Git absent from PATH. Check that the existing install can initialize its vault and preserve save/undo behavior, or document the exact blocker and accepted redistribution boundary for the integrator.

Read first: the claim, `docs/OLD_CODE_MAP.md`, `docs/TESTING.md`, desktop packaging scripts and PH8.1 in `NORTHSTAR.yaml`.

## Drift check

- Checkpoint: PH8.1. PH1 and PH7 are prerequisites; PH7 is done, PH1 remains in progress. No phase status changes.
- Properties/metrics: P-USABLE, P-MEMORY, P-CONTROL; M-RECOVER, M-AUDIT.
- Existing tools: current packaged Git integration and isolated PATH test; no new dependency or license exception.
- Acceptance first: with developer Git unavailable, installed app starts, creates a vault, commits a note and restores it; otherwise the claim records a precise failure and no workaround is adopted.

## Verification

Run only in a disposable install/home. Do not bundle a new executable, change license treatment, sign or publish. Owner approval remains required for a redistribution or release decision.
