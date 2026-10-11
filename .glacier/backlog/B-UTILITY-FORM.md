# B-UTILITY-FORM — Produce a reviewable unsigned utility application artifact

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-UTILITY-FORM`; never push.

## Scope

Allowed edits: `new ventures/utility-audits/scripts/render_application.py; new ventures/utility-audits/forms/ source metadata and approved blank template; new ventures/utility-audits/FORM-PROOF.md`. Also allowed: `evidence/backlog/B-UTILITY-FORM/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **utility**. Work on existing Indiana preparation only, without deciding the open state/fee/legal gates. Forms requiring a new dependency or rights decision go to a claim; no flow edits.

## Goal and evidence

The current command writes application-data JSON; the spec asks for filled forms for customer review/signature. The owner guide still requires completing the official form manually.

Render the already-validated application data into an unsigned review copy of the owner-selected official form, preserving blank/uncertain fields and source revision. Do not add eligibility calculations or choose a launch state.

Read first:

- [ventures/utility-audits/scripts/utility_audit.py](../../ventures/utility-audits/scripts/utility_audit.py) (prepare_st200)
- [ventures/utility-audits/PROOF.md](../../ventures/utility-audits/PROOF.md)
- [ventures/SPEC.md](../../ventures/SPEC.md) (Utility audits outputs)

## Drift check

- Checkpoint: **PH12.18**. Properties: **P-USABLE, P-VERIFY**. Metrics: **M-INTERVENE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Reuse existing pinned PDF libraries; verify official form version and redistribution terms before bundling.
- Value/effort estimate: **3/5 value ÷ 3 effort units = 1.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent known input values appear in the corresponding current form fields; missing values remain visibly incomplete; signature fields stay blank. Compare rendered pages to source data and label the result a draft.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/utility-audits/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
