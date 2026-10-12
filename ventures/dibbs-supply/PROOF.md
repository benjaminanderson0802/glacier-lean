# DIBBS venture proof

## Fixture and local checks

- The independent SAM.gov v2 acceptance fixture is a synthetic `opportunitiesData` response envelope. `parse_sam_opportunities` normalizes and ranks its DLA record for the supplied NAICS set; the acceptance fixture contains no API key. This verifies parsing only, not SAM.gov connectivity.
- `venture.json` declares the owner-provided `sam_api_key` under `secrets_needed`; runtime code resolves it from Glacier Secrets. No API key is stored in this repository or acceptance fixture.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest ventures/dibbs-supply -q` — **18 passed, 2 xpassed**. The xpassed checks are the implemented parser and named-secret acceptance checks. Existing venture tests cover exact solicitation/part/supplier checks, eligibility and electronics filters, margin ranking, CSV field mapping, authorization/traceability, quote-request drafts, API request filters and pagination, ranking, and owner gates.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest ventures/dibbs-supply/tests/acceptance -q --runxfail` — **4 passed**; acceptance assertions were not edited.
- `git diff --check` — **passed**.
- Fixture-mode preparation using `tests/fixtures/sam-opportunities-v2.json`, one synthetic DIBBS detail record, and one owner-entered synthetic supplier quote — **1 opportunity ranked, 1 bid ranked, `quote.csv` written, `submitted` false**. The fixture is synthetic and reflects the documented v2 response shape; it is not a live source result.
- `/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only dibbs-supply --dry-run` — **both flows validated**.

## Real Glacier flow

- Started the real FastAPI backend with a disposable `GLACIER_HOME`, installed both DIBBS flows, and ran `dibbs-daily-prep` through the backend (run `eb8bc0293f82`). The run reached `done`; the command check passed and the uncertainty note was saved. The `prepare` command correctly reported `live_source_checked: false` and `SAM.gov is not configured. Add sam_api_key in Glacier Settings > Secrets.` No API request was made. This proves the missing-key path in the real runtime, not live SAM access.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest ventures -q` — collection fails for existing import-path collisions in `recall-actor` and `utility-audits`. Running suites from their venture folders passed for Apify (10), Carpenter (6), Co-op postcards (9), CPSC (18), FDA cosmetics (9), Freight claims (23), OSHA (8), Property tax (6), Recall actor (10 passed, 1 skipped), Utility audits (9), and Warranty (17).
- The `recall-checker` suite has **1 unrelated existing failure**: `test_clean_item_uses_required_source_and_date_vocabulary` expects `no match ...`, while the implementation returns `no match found ...` (10 passed, 1 failed). It is outside this card and was not changed.
- `PYTHONPATH=<repo> python -m pytest -q ventures/tests` — 15 passed, 1 unrelated existing installer test failed because it assumes only two Apify flows. `PYTHONPATH=<repo> python -m pytest -q ventures/blocks` — 58 passed, 3 portal-filer tests failed because Playwright is unavailable in this worktree.

## Live SAM.gov source

The daily feed now calls the official [SAM.gov Contract Opportunities API v2](https://open.gsa.gov/api/get-opportunities-public-api/) endpoint, requests each configured NAICS code with an organization filter for DLA, locally verifies returned DLA department/organization fields and NAICS, paginates, and marks page caps as incomplete. The owner's free public key must be added through Glacier Secrets as `sam_api_key` before live API behavior can be verified. No key is configured here, so the live API-key canary has **not** been run; fixture parsing is not a live canary. No live opportunities, account, supplier quote, purchase, signature, or agency submission is claimed.

DIBBS still presents a DoD warning/consent page to public-page probes. Glacier does not browse through or acknowledge it. SAM.gov notices are discovery candidates only: the owner verifies each on DIBBS and supplies the exact DIBBS URL, eligibility, item, quantity, deadline, and quote requirements before a bid sheet can be prepared.

## Remaining verification

- Live SAM.gov API response, pagination against production data, and quote-sheet generation from the owner's actual supplier quotes remain unverified until the owner saves `sam_api_key` and supplies real records.
- PH12.19 remains in progress; no checkpoint status was changed.
