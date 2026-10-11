# B-READER-OCR — Provide a reproducible local photo-reading prerequisite

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-READER-OCR`; never push.

## Scope

Allowed edits: `new ventures/blocks/reader/setup_ocr.py; new ventures/blocks/reader/OCR-SETUP.md; ventures/blocks/reader/reader.py only for executable discovery`. Also allowed: `evidence/backlog/B-READER-OCR/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **reader-runtime**. Preserve the reader API consumed by RG-FDA and RG-WARRANTY. B-READER-LABELS owns evaluation data; this builder never labels its own benchmark.

## Goal and evidence

The recorded image path was blocked by a missing Tesseract executable; text-model availability does not prove image extraction.

Detect a pinned OSI-licensed Tesseract installation and provide isolated setup instructions plus useful missing-tool diagnostics. Use the existing OCR implementation and keep missing second-engine results uncertain.

Read first:

- [vault/claims/2026-10-10-b1-reader-image-ocr.md](../../vault/claims/2026-10-10-b1-reader-image-ocr.md)
- [ventures/blocks/reader/CHECK.md](../../ventures/blocks/reader/CHECK.md)

## Drift check

- Checkpoint: **PH12.4**. Properties: **P-PORTABLE, P-VERIFY**. Metrics: **M-LOCAL, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Tesseract plus the existing reader and Ollama adapter; check licensing and pins before install. No global environment changes.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Run the frozen independent image sample with real Tesseract and the configured local model; retain field/page/confidence results. Missing OCR and missing model both fail closed. Linux proof is distinct from owner Windows installation.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/reader/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
