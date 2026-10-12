# U-FIX1 verification

## Passed

- `npm run build`
- `npx tsc -b`
- `node e2e/theme_lint.mjs` — 58 files
- `node scripts/check-i18n.mjs --fail` — 965 keys, parity passed
- `node e2e/u-fix1.spec.mjs` — English and Spanish chrome, mixed-case venture content, live room status counts, and center scrolling at 1280x800, 1440x900, and 1920x1080; captured top and bottom screenshots at each size
- `node e2e/venture-summary.spec.mjs` — mock venture summary, run, and responsive screenshots
- `node e2e/spanish.spec.mjs` — Spanish screens at 1280x800 and 1024x700
- `node e2e/shell.spec.mjs` — painted shell and screen navigation

## Existing UI suite findings

- `npm run check:ui` stopped at `every_control.spec.mjs`. After syncing its mock dispatch approval fixture, `node e2e/every_control.spec.mjs` reports one remaining unrelated inert control: `build | button | (no test id) | interview`. The test itself identifies that screen as owned by another worker; its check was not changed.
- `node e2e/ventures.spec.mjs` stops at its `venture status is shown` expectation (`setting up`). The card currently renders `blocked` from the API readiness value while owner steps remain. The test was not changed.

The full UI board therefore does not pass on this base; these two existing findings are outside this card's screen changes.
