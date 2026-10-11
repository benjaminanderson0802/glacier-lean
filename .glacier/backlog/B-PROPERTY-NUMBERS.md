# B-PROPERTY-NUMBERS — Reject non-finite property values before preparing packets

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-PROPERTY-NUMBERS`; never push.

## Scope

Allowed edits: `ventures/property-tax/scripts/property_tax.py`. Also allowed: `evidence/backlog/B-PROPERTY-NUMBERS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **property**. Venture script only. The known approval-edge bug is reserved for V-AUTOMATE; this card must not touch flows or imply that customer launch is cleared.

## Goal and evidence

_number accepts positive float values without a finiteness check; Infinity can pass the positive-value branch. Reproduce impact on packet output before fixing.

Reject non-finite, malformed and unsupported monetary/area inputs consistently, retaining source-linked uncertainties and never emitting invalid valuation arithmetic.

Read first:

- [ventures/property-tax/scripts/property_tax.py](../../ventures/property-tax/scripts/property_tax.py) (_number, build_packet)

## Drift check

- Checkpoint: **PH12.17**. Properties: **P-VERIFY**. Metrics: **M-FALSE-DONE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Python math/decimal and existing parser; no appraisal model or new legal guidance.
- Value/effort estimate: **3/5 value ÷ 1 effort units = 3.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent cases for Infinity, NaN, huge exponents, zero, negative and valid formatted numbers yield deterministic uncertainty or valid finite output; existing self-file guidance stays intact.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
