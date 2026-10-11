# P-APIFY readiness test record — 2026-10-11

Interpreter: `~/w/glacier-lean/.venv/bin/python`. Test runs used `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`; no files under any `tests/acceptance/` directory were written or edited.

| Package/suite | Result | Notes |
| --- | --- | --- |
| `ventures/apify-tools/tests` | 17 passed, 1 skipped, 1 failed | The independent schema acceptance assertion expects output field names directly under `fields`; the requested Apify JSON Schema has `fields.type=object` and property names under `fields.properties`. Dispute in `ventures/apify-tools/DISPUTE.md`. The distinct publication-gate test passes when run alone. |
| `ventures/apify-tools-louisiana/tests` | 14 passed, 1 failed | Same disputed schema-shape assertion; see `ventures/apify-tools-louisiana/DISPUTE.md`. |
| `ventures/recall-actor/tests` | 13 passed, 2 skipped | Skips are opt-in live-source canaries. |
| `ventures/apify-census-permits/tests/acceptance` | 9 passed, 1 skipped | Source-outage wording regression now passes; live canary is opt-in. Windows socketpair report is recorded in `DISPUTE.md`; Linux worker did not reproduce it. |
| `ventures/apify-fdic-bankfind/tests/acceptance` | 10 passed, 1 failed, 1 skipped | Existing case-sensitive expected phrase is compared against a lowercased message; existing dispute retained. |
| `ventures/apify-npi-batch/tests/acceptance` | 11 passed, 1 failed, 1 skipped | Same impossible uppercase-after-lowercase assertion pattern; existing dispute retained. |
| `ventures/apify-portfolio/tests` | 33 passed | Covers all six package configs, event prices, listing sections, and the Census wording regression. |
| `ventures/tests` | 24 passed, 2 subtests passed | Manifest/owner-guide and installer suite. |

The two Mississippi/Louisiana schema failures are known acceptance disagreements, not product errors against the user-requested schema. FDIC/NPI failures are pre-existing assertion defects, not changed here. No protected acceptance check was weakened or edited.
