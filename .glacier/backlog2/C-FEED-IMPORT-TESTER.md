# C-FEED-IMPORT-TESTER — Independently verify owner-supplied snapshot provenance

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `feed-import-evaluator`. Allowed edits: new tests in `ventures/blocks/feeds/tests/` named with `C-FEED-IMPORT` and `evidence/backlog2/C-FEED-IMPORT-TESTER/`. No importer, registry or existing check edits.

## Goal

Verify the merged owner-downloaded import path preserves source URL, retrieval time, source vintage, file hash and row count; duplicate, malformed and mismatched files must remain untrusted and never overwrite a trusted snapshot. Use synthetic copies only.

Read first: `ventures/blocks/feeds/IMPORT.md`, `CHECK.md`, `sources.json`, commit `cbe35b5`, `NORTHSTAR.yaml` PH12.5.

## Drift check

- Checkpoint: PH12.5. PH5/PH9 remain in progress; PH12 feed work is authorized in parallel.
- Properties/metrics: P-VERIFY, P-MEMORY; M-VERIFIED, M-SURVIVE.
- Existing tools: imported snapshot API, file hashing and pytest; no new feed system.
- Acceptance first: only a fully validated dated source file is made available; imported data remains traceable to its exact bytes and cannot silently replace a trusted record after validation failure.

## Verification

Run the new independent checks and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests`. Do not submit owner data or contact a source; keep all downloaded-source examples already committed.
