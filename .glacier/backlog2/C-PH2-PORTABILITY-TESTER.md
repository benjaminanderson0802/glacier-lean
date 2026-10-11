# C-PH2-PORTABILITY-TESTER — Recheck the same goal on three worker backends

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `three-backend-evaluator`. Allowed edits: `evidence/backlog2/C-PH2-PORTABILITY-TESTER/` and a card-specific claim only. No route implementation, model prompt or benchmark edits.

## Goal

Run the exact same frozen goal and independent acceptance check through three already-supported backends, including a free local route, and record actual pass/fail, route and cost. Diagnose none of the workers by changing their task.

Read first: PH2 exit in `NORTHSTAR.yaml`, `bench/portable/`, claim `2026-10-10-e-ph2-portability.md`, `evidence/live/portable_three_backends.md`.

## Drift check

- Checkpoint: PH2 exit. PH1 remains `in_progress`; the card supplies evidence only and cannot claim the phase exit.
- Properties/metrics: P-PORTABLE, P-VERIFY; M-PORTABLE, M-COST.
- Existing tools: existing ACP/gateway backends and the portable benchmark; no new harness.
- Acceptance first: all three backends complete the identical goal and independent check (100% of selected routes); failures remain in the denominator and are reported with cost/route.

## Verification

Use isolated runs and the existing benchmark unchanged. If a backend is unavailable or incapable, save the raw result and file a claim; never substitute a different goal or weaken the check.
