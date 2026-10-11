# B-MAIL-SUPPRESSION — Honor do-not-mail requests across equivalent address spellings

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-MAIL-SUPPRESSION`; never push.

## Scope

Allowed edits: `ventures/blocks/mail/engine.py`. Also allowed: `evidence/backlog/B-MAIL-SUPPRESSION/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **mail**. Serialize with B-MAIL-SECRETS and B-MAIL-PROOF. This does not edit co-op or warranty flows.

## Goal and evidence

Suppression normalization currently lowercases joined components but preserves punctuation and internal whitespace. Equivalent representations may evade matching; reproduce with supplied addresses.

Normalize harmless spelling/format differences deterministically while preserving distinct apartment/unit identities. Recheck suppression on every prepare/send attempt and keep the list plain-text and durable.

Read first:

- [ventures/blocks/mail/engine.py](../../ventures/blocks/mail/engine.py) (_normalized_address, add_to_suppression, check_outreach)
- [ventures/SPEC.md](../../ventures/SPEC.md) (Outreach)

## Drift check

- Checkpoint: **PH12.7**. Properties: **P-CONTROL**. Metrics: **M-AUDIT, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing suppression file and address adapter; use an existing OSS normalizer only if needed and reviewed.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent fixtures vary case, whitespace, ZIP formatting and address aliases; each opted-out address stays blocked on the next run while another unit is not incorrectly suppressed. No postal request is made.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
