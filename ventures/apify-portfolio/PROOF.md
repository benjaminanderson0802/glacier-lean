# A-APIFY3 verification

The three additional Actor packages are implemented and locally source-tested. No Actor was logged into, uploaded, cloud-built, paid for, published or pushed. PH12.10 remains in progress; phase-wide acceptance belongs to the integrator.

## Commands and results (2026-10-10 UTC)

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-portfolio/tests ventures/tests` — **52 passed** (31 new regressions, 21 existing venture tests, including input schema and owner-guide checks). [Final log](evidence/tests-final.txt). Existing tests/acceptance and ACCEPTANCE.md are untouched. [Before implementation](evidence/tests-before.txt): 22 failures because implementation/packaging did not yet exist.
- `~/w/glacier-lean/.venv/bin/python ventures/apify-portfolio/live_canary.py` — real Apify SDK `python -m src` in each independent Git subfolder with isolated local INPUT/storage and cloud configuration removed. All exited 0: FDIC 1 bank, Census 3 state comparisons, NPPES 1 provider. Exact request URLs, UTC times, hashes and outputs: [FDIC](../apify-fdic-bankfind/PROOF.md), [Census](../apify-census-permits/PROOF.md), [NPI](../apify-npi-batch/PROOF.md). No fixtures injected into these runs.
- `cd glacier/web && node e2e/theme_lint.mjs` — **pass, 52 files**. [Log](evidence/theme.txt).
- `cd glacier/web && npx tsc -b` — **blocked**: project TypeScript unavailable through the pre-existing shared node_modules link. [Log](evidence/typescript.txt).
- `cd glacier/web && node scripts/check-i18n.mjs --fail` — **blocked**: `ERR_MODULE_NOT_FOUND` for typescript. [Log](evidence/i18n.txt).
- `cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_core.py` — **31 passed, 1 setup error**, 255.19 seconds. Real uvicorn backends exercised. One websocket test's server did not start within its fixture deadline, with an empty server log. [Log](evidence/backend-core.txt). No backend files/tests changed, no fix attempted outside this card.
- `git diff --check` — passes.

The broad shared board is not reported green. [Validation claim](../../vault/claims/2026-10-10-a-apify3-shared-validation.md) links the prior frontend dependency claim and the new backend startup evidence. The legacy full-board script mutates shared dependencies and a fixed /tmp directory, so it was inspected rather than run against other workers' resources. No UI screens or worker nodes changed; browser specs/live Codex execution do not cover these standalone Actors. No cloud Docker build claimed.

## Behavioral coverage

Real-shaped FDIC `meta/data[].data`, two-header 29-column Census CSV, and NPPES `result_count/results[].basic/addresses/taxonomies`. Tests cover exact IDs, source dates/vintage, dollar conversion, reported versus imputed units, page offsets/caps, duplicate pages, partial-page outage, identity mismatch, no-match versus source error, missing/non-numeric values, latest-month discovery, pre-request input rejection, serial rate limiting, bounded 429 retry, redirect refusal, paid-event caps/idempotency keys, exact requirements copies and identical vendored runtime, and JSON Schema validation of live output.

Billing tests use a fake Actor and prove event selection/cap behavior, not a real transaction. Owner configuration must use only the named custom events and disable synthetic start/default-dataset charges. Local canaries never charge. Apify platform costs and profitability require owner-controlled cloud measurements after build; store metrics do not prove revenue.

## Scope and review

Changed paths: `ventures/apify-{census-permits,fdic-bankfind,npi-batch}/`, `ventures/apify-portfolio/`, the Apify row/URL section in `ventures/OWNER-START-HERE.md`, and the required environment claim in `vault/claims/`. Pre-existing `.venv` and `glacier/web/node_modules` symlinks remain unstaged. No change to mission, roadmap statuses, checks, shared backend, UI, existing Actors or their pricing.

Anti-pattern review: software and live outputs accompany the research; no unsupported revenue/phase-complete claims or governance/framework build. No new runtime dependency or paid service. No protected test was edited. No anti-pattern correction required; docs/AMENDMENTS.md was left untouched outside this card's scope.

The exact deployment URLs target `glacier-final`; commit-only work must first be integrated there by the owner/integrator. All six existing/new package URLs and suggested prices are in [OWNER-START-HERE](../OWNER-START-HERE.md#apify-git-urls-and-prices).

## P-APIFY publish-readiness extension (2026-10-11)

Prepared all six existing Store Actors in place: Mississippi, Louisiana, Recall, Census, FDIC, and NPI. Every package now has an Actor definition, an input object schema, a dataset JSON Schema under `fields` (`type: object`, `properties`), Store README examples and pricing explanation, `pricing.json`, and owner steps. [`PUBLISH-CHECKLIST.md`](PUBLISH-CHECKLIST.md) has the six existing account IDs, exact Git URLs, titles, SEO descriptions, named events/prices, run caps, Console links, clicks, and one-sitting order. Package manifests are marked ready for these owner account actions; the unrelated broader Recall Checker workflow stays blocked by its FSIS feed gate.

Census source failures now use the required `uncertain - please check` customer wording. The Windows-only asyncio socketpair report is recorded in `ventures/apify-census-permits/DISPUTE.md`; no Windows traceback was supplied, and the Linux worker did not reproduce it. Network guards and acceptance files were not changed.

Test command totals and the disputed acceptance assertions are recorded in [`evidence/publish-readiness-tests-2026-10-11.md`](evidence/publish-readiness-tests-2026-10-11.md). Portfolio tests: 33 passed; `ventures/tests`: 24 passed, 2 subtests passed. Census acceptance: 9 passed, 1 skipped. Mississippi/Louisiana schema assertions and the pre-existing FDIC/NPI case assertions remain disputed in their respective `DISPUTE.md` files; no protected acceptance check was modified.

This prepares repository assets only. The owner must integrate the commit into `glacier-final`, verify payouts/business once, connect each existing Actor to Git, build, enter prices, review outputs, and publish. No account login, cloud build, price entry, charge, or publication was performed.
