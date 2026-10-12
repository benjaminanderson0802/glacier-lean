# FDA listing package preparation checks

Run on 2026-10-11 in this worktree. No Shopify production account or external service was modified.

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics -q` — 21 passed.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py -q --runxfail` — 3 passed; acceptance files were not modified.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/blocks/reader/tests/test_acceptance.py -q` — 3 passed. This does not close the separate B1-owned claim.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` — 24 passed, 2 subtests passed.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — `prepare-listing-packet` and `daily-deadline-reminders` validated.
- `npm test` in `ventures/shopify-fda-app` — 6 passed.
- `npm run typecheck` in `ventures/shopify-fda-app` — passed.
- `npm run build` in `ventures/shopify-fda-app` — passed.
- `npm audit --omit=dev` in `ventures/shopify-fda-app` — reports 7 vulnerabilities (6 high, 1 low). See claim `CLM-2026-10-11-P-FDA-SHOPIFY-APP-DEPENDENCY-SECURITY`; no dependency files were changed.

The App Store icon is 1200×1200, feature image 1600×900, and all three screenshots 1600×900. The listing assets use the checked-in synthetic fixture. These checks do not prove that the production URL/privacy page is live or that Shopify will approve the app.
