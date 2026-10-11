---
id: CLM-2026-10-10-B-FILER-SETUP-ACTIONABILITY
filed_by: Codex
run_id: card/B-FILER-SETUP
node_id: ventures.blocks.filer
checkpoint: PH12.7
kind: bug
summary: With the filer-local Playwright install resolving successfully, the repo-root mock acceptance suite still intermittently times out waiting for the login button to become actionable.
evidence: evidence/backlog/B-FILER-SETUP/verification.md; repo-root `pytest -q ventures/blocks/filer/tests` with disposable filer `node_modules` on NODE_PATH: 3 failures at `runner.mjs` login-button click after 20 seconds; the same unchanged suite passed 3/3 in a fresh disposable filer tree.
attempts_made: 0 code-fix attempts; stopped at the NORTHSTAR stuck signal.
status: filed
assigned_to: debugger
resolution: ""
resolution_evidence: ""
---

This reproduces the login-button actionability issue previously recorded in [claim-ph12-7-playwright-actionability](2026-10-09-ph12-7-playwright-actionability.md) while verifying the new filer-local dependency setup. The isolated clean install passed all three mock acceptance cases; a separate repo-root invocation hit the existing visibility/stability timeout in all three cases. The worker stopped without modifying the interaction or retrying after the stuck signal.
