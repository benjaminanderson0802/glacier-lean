# Live and fixture proof — Census Building Permits State Change Feed

Date: 2026-10-11T03:03:36.311216+00:00 to 2026-10-11T03:03:38.531430+00:00 (UTC). Actual Python Apify SDK entrypoint, local storage, no token/cloud billing; exit 0, 3 dataset rows, all `ok`. This proves the local source path and SDK lifecycle, not an Apify cloud build or public listing.

Command from repository root: `~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py` invokes `python -m src` in each Actor folder with a temporary local INPUT and storage directory. It removes APIFY/ACTOR/CRAWLEE environment variables first and forces local mode. [Captured input and complete output](evidence/local-output.json); [SDK log](evidence/local-main.log).

Actual requested URLs:

- https://www2.census.gov/econ/bps/State/st2607c.txt
- https://www2.census.gov/econ/bps/State/st2608c.txt

Result: Alabama; record `01:2026-08:2026-07`. Each row includes retrieval time and SHA-256 of the official response. Census also preserves the prior-period URL/hash.

Fixtures preserve the real response envelopes captured from the same official sources: [FDIC](../apify-portfolio/evidence/fdic-source.txt), [NPPES](../apify-portfolio/evidence/npi-example.json), [Census July](../apify-portfolio/evidence/st2607c.txt) / [August](../apify-portfolio/evidence/st2608c.txt). Synthetic failure/pagination cases derive from those envelopes and are labeled in test names. They are not live outage evidence.

Regression suite and existing venture suite: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests` → **52 passed**; [log](../apify-portfolio/evidence/tests-final.txt). Before implementation, the new tests failed on missing modules/packaging: [test-first evidence](../apify-portfolio/evidence/tests-before.txt). No existing test or acceptance file changed.

Billing was exercised through a fake Actor: success-only event, no event on uncertain/no-match, idempotency key and spending-cap stop. No paid event or cloud deployment was performed. Owner must configure only the custom event listed in README; automatic dataset/start pricing would charge outage results.

Remaining shared-board limits: see [portfolio PROOF](../apify-portfolio/PROOF.md). No phase is marked complete. Git URL targets `glacier-final`; this work is commit-only on the assigned branch, so integration by the owner/integrator is needed before that URL contains these files.
