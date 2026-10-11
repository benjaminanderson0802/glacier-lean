# B-FEED-IMPORT — Import owner-downloaded official data with provenance

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-FEED-IMPORT`; never push.

## Scope

Allowed edits: `new ventures/blocks/feeds/import_snapshot.py; ventures/blocks/feeds/core.py only for a shared validated import seam; new ventures/blocks/feeds/IMPORT.md`. Also allowed: `evidence/backlog/B-FEED-IMPORT/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **feeds**. Serialize after B-FEED-QUARANTINE. Existing venture scripts remain read-only; wire caller changes only through their separately assigned owners.

## Goal and evidence

FSIS/OSHA access and DIBBS consent are explicitly blocked in the live source report; the documented fallback is an owner-downloaded official file.

Offer a bounded offline import for the existing supported source schemas, recording source URL, acquisition date, hash, format, row count and completeness. Apply the same canary/quarantine policy as network refresh.

Read first:

- [ventures/blocks/feeds/CHECK.md](../../ventures/blocks/feeds/CHECK.md)
- [ventures/blocks/feeds/sources.json](../../ventures/blocks/feeds/sources.json)
- [vault/claims/2026-10-10-b2-fsis-api-403.md](../../vault/claims/2026-10-10-b2-fsis-api-403.md)

## Drift check

- Checkpoint: **PH12.5**. Properties: **P-LOOPS, P-VERIFY**. Metrics: **M-VERIFIED, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing source normalizers and SQLite; no anti-bot workaround or new paid feed.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent saved source files import with traceable provenance; malformed, stale, HTML error and incomplete inputs do not replace good data. Reimporting identical bytes is idempotent and never claims a live fetch.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
