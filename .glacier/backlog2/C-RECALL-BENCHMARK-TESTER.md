# C-RECALL-BENCHMARK-TESTER — Build the independent recall-matcher release set

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `recall-benchmark-evaluator`. Allowed edits: new independently sourced labels under `ventures/recall-checker/bench/` and `evidence/backlog2/C-RECALL-BENCHMARK-TESTER/`; no matcher, benchmark runner or existing acceptance edits. Use only public recall records and synthetic clean inventory rows.

## Goal

Address the missing 500 known-recalled / 500 known-clean independent release set. Record source IDs, dates and expected match outcomes before running the unchanged checker. Do not reuse the checker’s own output to label examples or claim recall completeness.

Read first: claim `2026-10-10-ph12-12-recall-benchmark-engine.md`, `ventures/recall-checker/ACCEPTANCE.md`, `PROOF.md`, `bench/` and `ventures/SPEC.md` global output rules.

## Drift check

- Checkpoint: PH12.12. PH5/PH9 remain in progress; PH12 is owner-authorized parallel work.
- Properties/metrics: P-VERIFY; M-FALSE-DONE, M-VERIFIED.
- Existing tools: existing public feeds, matcher and benchmark harness; no new data vendor.
- Acceptance first: frozen 1,000-item set has source-backed labels and hash manifest; report false-no-match rate with the full denominator and required borderline second-engine route as a separate check.

## Verification

Run the unchanged release benchmark only after labels are committed. Keep source attribution and license/terms notes. If 1,000 reliable labels cannot be assembled from approved public data, file a capability-gap claim instead of lowering the sample target.
