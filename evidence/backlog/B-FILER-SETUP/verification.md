# B-FILER-SETUP verification

## Dependency reproduction and clean install

- Before implementation, `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests` failed all 3 acceptance cases with Node `MODULE_NOT_FOUND` from `runner.mjs`.
- In a fresh `/tmp` tree containing the unchanged filer tests and implementation, `npm ci --prefix <tmp>/ventures/blocks/filer` installed the pinned dependencies (2 packages; 0 vulnerabilities).
- `npx --prefix <tmp>/ventures/blocks/filer playwright install chromium` completed successfully.
- From that disposable tree, `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/filer/tests` passed: **3 passed in 2.87s**. The local mock checks verified prepare without submission, approval-gated submission, and no duplicate filing on confirmation replay.

## Follow-up root run

The repo-root suite was run with the disposable Playwright installation exposed using `NODE_PATH` (the shared `glacier/web/node_modules` was not changed). Dependency resolution succeeded, but all 3 tests then stopped at the existing login-button actionability timeout (`locator.click`, 20 seconds). This is the stuck signal covered by [claim-ph12-7-playwright-actionability](../../../vault/claims/2026-10-09-ph12-7-playwright-actionability.md); no interaction changes or retry were attempted. See [the B-FILER-SETUP claim](../../../vault/claims/2026-10-10-b-filer-setup-actionability.md).

All browser evidence here is fixture/local mock evidence. No real portal, account or filing was used.
