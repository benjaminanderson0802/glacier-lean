# B-MAIL-PROOF — Make local postcard proofs show all of the reviewed content

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-MAIL-PROOF`; never push.

## Scope

Allowed edits: `ventures/blocks/mail/engine.py; new ventures/blocks/mail/PROOF-LIMITS.md`. Also allowed: `evidence/backlog/B-MAIL-PROOF/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **mail**. Exclusive mail lane; no shared web dependencies, co-op flows or design approval changes.

## Goal and evidence

_proof_pdf strips HTML and silently truncates text to sixteen lines. A proof can omit content the owner is expected to approve.

Render complete local previews or fail visibly on overflow. Distinguish the standard 4x6 preview from the separate co-op EDDM dimensions; do not label a text proof print-ready.

Read first:

- [ventures/blocks/mail/engine.py](../../ventures/blocks/mail/engine.py) (_proof_pdf)
- [ventures/coop-postcards/README.md](../../ventures/coop-postcards/README.md)

## Drift check

- Checkpoint: **PH12.7**. Properties: **P-USABLE, P-CONTROL**. Metrics: **M-VERIFIED, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Reuse available pinned browser/PDF rendering rather than extending the hand-written PDF layout engine.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent long-copy and styled-copy examples include all text and sender details or return an explicit blocking overflow result. Render and inspect both pages at stated dimensions; no order or send.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
