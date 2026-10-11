# B-READER-LABELS — Independently complete the reader release benchmark

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-READER-LABELS`; never push.

## Scope

Allowed edits: `ventures/blocks/reader/samples/manifest.json; new files under ventures/blocks/reader/samples/documents/; new ventures/blocks/reader/samples/LABEL-PROVENANCE.md`. Also allowed: `evidence/backlog/B-READER-LABELS/` and a card-specific claim in `vault/claims/`. Tester-only: the scope above is the full check/data authorization. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **reader-evaluator**. Assign to an independent evaluator who has not built the reader or FDA implementation. No edits to reader.py, benchmark.py or existing checks; schedule local-model access without taking another worker’s process.

## Goal and evidence

Four of seven public samples have empty label arrays. The checkpoint still links a queued release benchmark rather than a measured two-engine result.

Tester-only assignment: independently label representative fields and blank/uncertain cases from source documents, with page provenance. Freeze labels before running the unchanged benchmark and publish its actual denominator and agreement.

Read first:

- [ventures/blocks/reader/samples/manifest.json](../../ventures/blocks/reader/samples/manifest.json)
- [ventures/blocks/reader/CHECK.md](../../ventures/blocks/reader/CHECK.md)
- [vault/claims/2026-10-10-b1-reader-benchmark-lock.md](../../vault/claims/2026-10-10-b1-reader-benchmark-lock.md)

## Drift check

- Checkpoint: **PH12.4**. Properties: **P-VERIFY**. Metrics: **M-VERIFIED, M-FALSE-DONE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing benchmark and public documents; no new evaluation framework.
- Value/effort estimate: **5/5 value ÷ 2 effort units = 2.50**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Use the existing >=95% release criterion, two genuinely separate engines, hash-matched public inputs and missing-engine negative cases. Report every disagreement; do not tune labels or reader code after observing results.

Run `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.reader.benchmark ventures/blocks/reader/samples/manifest.json`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
