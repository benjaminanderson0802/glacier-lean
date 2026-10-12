# C-PH9-MAINTENANCE-BOARD-TESTER — Independently run the maintenance Environment safely

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `maintenance-board-evaluator`. Allowed edits: `evidence/backlog2/C-PH9-MAINTENANCE-BOARD-TESTER/` and a card-specific claim. Do not edit `setup/run_core_tests.sh`, `setup/live_codex_check.sh`, the maintenance flow or its checks.

## Goal

Verify the maintenance Environment completes in a fresh clone using isolated dependency directories, a unique home and authenticated/free-port backend helpers. It must produce a proposal note and leave the checkout unchanged. Separately record why the legacy shell launchers are unsafe, without executing their destructive fixed-path behavior.

Read first: claim `2026-10-10-e-ph9-legacy-test-board.md`, `NORTHSTAR.yaml` PH9.1, `docs/TESTING.md`, the maintenance Environment evidence.

## Drift check

- Checkpoint: PH9.1. PH3/PH5/PH7 gates apply; PH3 and PH7 exits are owner-approved, PH5 remains in progress.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: pytest isolated homes, current authenticated backend e2e and maintenance flow; no duplicate runner.
- Acceptance first: proposal is generated, no repository files change, and no shared dependency, fixed port or `/tmp/e2edata` is touched.

## Verification

Use a disposable clone, unique GLACIER_HOME and port. Run relevant maintenance tests and capture `git status`; never run the legacy launcher unchanged or stop another worker's process.
