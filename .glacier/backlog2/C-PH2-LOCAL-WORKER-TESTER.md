# C-PH2-LOCAL-WORKER-TESTER — Prove a local model executes a verified file task

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `local-worker-evaluator`. Allowed edits: `evidence/backlog2/C-PH2-LOCAL-WORKER-TESTER/` and a card-specific claim only. Do not edit prompts, worker routes, benchmark cases or tests that judge the worker.

## Goal

Independently run the existing small local coding goal on an available free local model through Glacier, offline, and verify the created artifact with a separate deterministic check. This directly addresses PH2.2's live-proof gap and the repeated Granite/OpenCode tool-use failure.

Read first: `NORTHSTAR.yaml` PH2.2, `evidence/ph2/RESULTS.md`, claim `2026-10-10-e-ph2-live-gaps.md`, `2026-10-10-e-ph2-portability.md`, `bench/portable/`.

## Drift check

- Checkpoint: PH2.2. PH1 is in progress; PH2 work may start but no exit is claimed.
- Properties/metrics: P-PORTABLE, P-VERIFY; M-PORTABLE, M-LOCAL.
- Existing tools: configured Ollama/MAF route and existing coding benchmark; no new model/service.
- Acceptance first: one documented local route creates the expected file offline, its deterministic independent check passes, and route/model/cost evidence is recorded.

## Verification

Run the frozen goal through a fresh isolated Glacier home, then the unchanged focused backend tests. If the model or engine is unavailable, record a capability/environment claim and stop; do not change the goal, use a paid route or accept prose as file work.
