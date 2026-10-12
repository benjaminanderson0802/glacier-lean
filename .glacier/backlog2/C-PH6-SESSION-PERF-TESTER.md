# C-PH6-SESSION-PERF-TESTER — Measure cold coding-session discovery without hiding records

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `session-discovery-evaluator`. Allowed edits: `evidence/backlog2/C-PH6-SESSION-PERF-TESTER/` and a card-specific claim. No session-reader implementation, user session files, or existing benchmark edits.

## Goal

On generated synthetic session files, measure cold and warm listing after the latest E-PH6 optimization. Check that the full session count, title, timestamp semantics and redaction remain intact while reporting timing and file volume.

Read first: claim `2026-10-10-e-ph6-cold-session-list.md`, `glacier/backend/sessions.py`, `NORTHSTAR.yaml` PH6.2, existing session tests.

## Drift check

- Checkpoint: PH6.2. PH2/PH5 remain in progress; PH6 stays in progress. This is a bounded performance evaluation, not owner-use evidence.
- Properties/metrics: P-PORTABLE, P-MEMORY, P-USABLE; M-INTERVENE, M-COST.
- Existing tools: current session reader and test fixtures; no index/cache is introduced by the tester.
- Acceptance first: report cold/warm time and exact count for a fixed generated corpus; no session is sampled, omitted or read from a real user corpus.

## Verification

Run relevant session unit tests and the existing profiling command on the fixed synthetic corpus. Report machine load and raw timing; do not claim a five-second target unless measured on comparable hardware.
