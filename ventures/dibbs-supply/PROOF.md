# DIBBS venture proof

## Checks run

- `.venv/bin/python -m pytest -q ventures/dibbs-supply/tests/test_dibbs_supply.py` — **11 passed**. Fixtures verify exact solicitation/part/supplier checks, eligibility/electronics filters, margin ranking, CSV output fields, traceability/authorization evidence, prefilled quote-request drafts, and owner gates. Fixture files are synthetic and do not count as real quotes.
- `.venv/bin/python ventures/install_all.py --only dibbs-supply --dry-run` — **validated** `dibbs-supply` / `dibbs-daily-prep`.
- `.venv/bin/python -m compileall -q ventures/dibbs-supply/scripts ventures/dibbs-supply/tests` — **passed**.

## Live public source

Command: `GLACIER_HOME=/tmp/glacier-dibbs-live .venv/bin/python -m ventures.blocks.feeds.cli sync dla_dibbs`

Output: `rows: 0`, `changed: false`, alert `Feed sync alert (dla_dibbs): ValueError: source returned no records; existing snapshot retained`. Read-only probes of the configured public landing page and `/rfq/` redirected to DIBBS's DoD warning/consent page. No consent acknowledgement, login, account creation, or submission was attempted. This repeats blocker `CLM-2026-10-10-B2-DIBBS-PUBLIC-FEED` in [the shared-block claim](../../vault/claims/2026-10-10-b2-dibbs-public-feed.md). The source check has not passed and PH12.19 remains **in progress**.

## Real Glacier flow

Pending heavy-wrapped `npm run live` install and dry-run. No screenshot is claimed until the live flow and approval screen are exercised.

## Limits

DIBBS's current shared `dla_dibbs` adapter is public-link discovery only, not a documented complete solicitation feed. The venture keeps feed alerts visible and does not infer solicitation eligibility, part identity, instructions, authorization, or traceability. No SAM.gov/CAGE account, supplier contact, purchase, signature, bid, or agency submission is performed by this venture.
