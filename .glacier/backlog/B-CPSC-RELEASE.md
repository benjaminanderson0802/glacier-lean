# B-CPSC-RELEASE — Prevent a changed CPSC template from silently changing batch output

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-CPSC-RELEASE`; never push.

## Scope

Allowed edits: `ventures/cpsc-prep/scripts/cpsc_prep.py; ventures/cpsc-prep/scripts/refresh_cpsc_sources.py`. Also allowed: `evidence/backlog/B-CPSC-RELEASE/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **cpsc**. Use B-FEED-QUARANTINE contract after integration if needed; no shared feed, reader, active-flow or acceptance edits. Counsel and broker-contract approval stay owner-only.

## Goal and evidence

refresh_cpsc_sources reports review-required changes after syncing. The batch consumer needs an explicit proof it cannot use a changed, unreleased template.

Bind generated registry files to a validated source/template revision and stop batch generation on unreleased schema changes. Keep absent fields blank with a gap list and cite the exact local revision used.

Read first:

- [ventures/cpsc-prep/scripts/refresh_cpsc_sources.py](../../ventures/cpsc-prep/scripts/refresh_cpsc_sources.py)
- [ventures/cpsc-prep/ACCEPTANCE.md](../../ventures/cpsc-prep/ACCEPTANCE.md)
- [ventures/SPEC.md](../../ventures/SPEC.md) (CPSC checks)

## Drift check

- Checkpoint: **PH12.9**. Properties: **P-VERIFY, P-CONTROL**. Metrics: **M-FALSE-DONE, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing template parser, rules checker and feed metadata; minimal consumer glue.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent old/new template fixtures prove column order is exact, removed/added required columns block release, and repeat processing on an approved unchanged revision is deterministic. Do not certify or submit anything.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/cpsc-prep/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
