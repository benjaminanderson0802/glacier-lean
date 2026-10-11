# B-FILER-SETUP — Make the portal filer runnable from a clean worktree

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-FILER-SETUP`; never push.

## Scope

Allowed edits: `ventures/blocks/filer/runner.mjs; new ventures/blocks/filer/package.json and package-lock.json; new ventures/blocks/filer/SETUP.md`. Also allowed: `evidence/backlog/B-FILER-SETUP/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **filer**. No active-card dependency; take the exclusive lane before editing.

## Goal and evidence

Fresh T-FIND run reproduced all three filer checks failing with MODULE_NOT_FOUND. runner.mjs resolves Playwright from the web workspace.

Give the filer a documented, pinned, worktree-local Playwright installation and resolver. Reuse the repository pin; leave the shared web node_modules and desktop packaging alone.

Read first:

- [ventures/blocks/filer/runner.mjs](../../ventures/blocks/filer/runner.mjs)
- [vault/claims/2026-10-10-ph12-14-filer-playwright-missing.md](../../vault/claims/2026-10-10-ph12-14-filer-playwright-missing.md)
- [ventures/OWNER-GUIDE-TESTS.md](../../ventures/OWNER-GUIDE-TESTS.md)

## Drift check

- Checkpoint: **PH12.7**. Properties: **P-LOOPS, P-VERIFY**. Metrics: **M-VERIFIED, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing Playwright and npm lockfiles; dependency wiring only, no replacement browser driver.
- Value/effort estimate: **5/5 value ÷ 1 effort units = 5.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

In a fresh disposable directory, install the pinned filer dependencies and run the unchanged local portal suite: prepare never submits, approval is required, confirmation replay does not double-file.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
