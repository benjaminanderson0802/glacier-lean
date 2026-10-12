# Live and fixture proof — FDIC BankFind Institution Normalizer

Date: 2026-10-11T03:03:34.907171+00:00 to 2026-10-11T03:03:36.299335+00:00 (UTC). Actual Python Apify SDK entrypoint, local storage, no token/cloud billing; exit 0, 1 dataset rows, all `ok`. This proves the local source path and SDK lifecycle, not an Apify cloud build or public listing.

Command from repository root: `~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py` invokes `python -m src` in each Actor folder with a temporary local INPUT and storage directory. It removes APIFY/ACTOR/CRAWLEE environment variables first and forces local mode. [Captured input and complete output](evidence/local-output.json); [SDK log](evidence/local-main.log).

Actual requested URLs:

- https://api.fdic.gov/banks/institutions?filters=CERT%3A3510&fields=CERT%2CNAME%2CACTIVE%2CSTALP%2CCITY%2CZIP%2CDATEUPDT%2CWEBADDR&format=json&sort_by=CERT&sort_order=ASC&limit=100&offset=0

Result: Bank of America, National Association; record `3510`. Each row includes retrieval time and SHA-256 of the official response. Census also preserves the prior-period URL/hash.

Fixtures preserve the real response envelopes captured from the same official sources: [FDIC](../apify-portfolio/evidence/fdic-source.txt), [NPPES](../apify-portfolio/evidence/npi-example.json), [Census July](../apify-portfolio/evidence/st2607c.txt) / [August](../apify-portfolio/evidence/st2608c.txt). Synthetic failure/pagination cases derive from those envelopes and are labeled in test names. They are not live outage evidence.

Regression suite and existing venture suite: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests` → **52 passed**; [log](../apify-portfolio/evidence/tests-final.txt). Before implementation, the new tests failed on missing modules/packaging: [test-first evidence](../apify-portfolio/evidence/tests-before.txt). No existing test or acceptance file changed.

Billing was exercised through a fake Actor: success-only event, no event on uncertain/no-match, idempotency key and spending-cap stop. No paid event or cloud deployment was performed. Owner must configure only the custom event listed in README; automatic dataset/start pricing would charge outage results.

Remaining shared-board limits: see [portfolio PROOF](../apify-portfolio/PROOF.md). No phase is marked complete. Git URL targets `glacier-final`; this work is commit-only on the assigned branch, so integration by the owner/integrator is needed before that URL contains these files.
