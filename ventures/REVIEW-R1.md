# PH12.22 independent venture review (R1)

Review scope: CPSC, Apify, warranty and recall. Source/spec references below refer to the named venture branches; tests were run in each branch checkout. I attempted a no-commit merge of `card/gf-V-APIFY` into `card/gf-R1`; it stopped on add/add conflicts in `ventures/SPEC.md` and `ventures/install_all.py`, so I aborted rather than resolve shared files outside this review. B1 and CPSC are already in this checkout. No venture code or test was changed.

## CPSC data prep

Spec: `ventures/SPEC.md:285-301`.

| Field | Status | Finding |
| --- | --- | --- |
| Purpose | partial | Described and implemented as a draft-prep pipeline; no real batch can run through it yet (`ventures/cpsc-prep/README.md`, `scripts/cpsc_prep.py`). |
| Inputs | partial | JSON batch/PDF reader path exists; live template, rule and flagged-code source IDs are not in `ventures/blocks/feeds/sources.json`. |
| Outputs | partial | Draft CSV, gaps and status data are implemented; current CPSC template and broker board were not demonstrated. |
| Blocks | partial | Reader/rules/feed/customer/mail functions are named in `venture.json`; source refresh failed before data retrieval and the feed registry lacks the three CPSC IDs. |
| Loop | partial | Batch preparation and daily refresh flows exist; second engine depends on local Ollama configuration (`GLACIER_OLLAMA_URL`, `GLACIER_LOCAL_MODEL`); no live end-to-end batch. |
| Checks | partial | Unit checks cover blanks, agreement and CSV shaping; exact current CPSC template/list checks have no real feed data. |
| Approval gates | done | `cpsc-batch-prep` gates CSV generation on customer certification; `cpsc-broker-launch` gates launch on the attached lawyer opinion and first-contract approval. |
| Billing | partial | Direct checkout plans are defined; broker amount is null and checkout is test-only until configured. |
| Edge cases | partial | Missing fields and uncertain readings are held; the three-failure unfamiliar-format policy/refund is not implemented as an observable workflow. |

Real data: `ventures/cpsc-prep/scripts/refresh_cpsc_sources.py` returned no counts. On the venture branch it failed because `ventures.blocks.reader` was unavailable; with the integrated block package on `PYTHONPATH`, `load_blocks()` failed at `cpsc_prep.py:313` with `NameError: read_document`. No CPSC source request was made. Also, the current feed registry has no `cpsc_flagged_tariff_codes`, `cpsc_rule_codes` or `cpsc_registry_template` entries, so fixing the import alone will still leave refresh unable to fetch data.

Tests: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/cpsc-prep/tests` → **13 passed**.

Owner steps: three; the corresponding Glacier approval flows explain the lawyer opinion, contract review and batch certification, but the owner checklist has no exact links. The README names required Ollama environment variables and Stripe test setup outside the three steps. The first broker contract and lawyer gate are appropriate approval gates; per-batch customer certification is required before output release.

Fixes, prioritized:

1. `ventures/cpsc-prep/scripts/cpsc_prep.py:load_blocks()` — bind imports under non-shadowed names and prove the refresh command imports successfully; the current class-body assignment crashes.
2. `ventures/blocks/feeds/sources.json` plus the CPSC feed adapter — add current official flagged-code, rule-code and template sources with canaries and reported counts; refresh has no registered IDs today.
3. `ventures/cpsc-prep/venture.json` / owner review flow — expose exact lawyer-opinion, per-batch certification and contract instructions/links, and surface the currently hidden local-model and test-payment setup before launch.

## Apify data tools

Spec: `ventures/SPEC.md:342-356` (no edge-case field is specified in this section).

| Field | Status | Finding |
| --- | --- | --- |
| Purpose | done | One Mississippi contractor license lookup Actor is built (`ventures/apify-tools/src/lookup.py`). |
| Inputs | done | License number and name searches are accepted. |
| Outputs | done | Literal status, expiration, direct source URL and unverifiable result are returned. |
| Blocks | partial | Public government source is queried directly; the documented shared government-feed block is not used. Apify handles billing. |
| Loop | partial | Three-license daily canary and first-publish gate exist; the spec's reusable multi-state factory and separate-engine review are not present. |
| Checks | done | Three live canaries matched; rate limiting and source-failure classifications are tested. |
| Approval gates | partial | First Actor has an owner approval flow; the spec says first three publishes require approval, which is not represented for later new Actors. |
| Billing | partial | `$0.02` event configuration is present; there is no deployed Store listing or owner-set account billing. |
| Edge cases | missing | The Apify spec section defines no edge-case behavior; implementation handles source failure/login/CAPTCHA limits in code/docs but there is no spec field to judge against. |

Real data: `ventures/apify-tools/scripts/daily_canary.py` → **3/3** live records matched: 22649, 18583 and 21881; all `Licensed`, with expirations 2027-05-07, 2027-03-18 and 2027-10-27. No failed canary; health `healthy`. Requests were spaced by the script. See `ventures/apify-tools/tests/canaries.json` for expected values.

Tests: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-tools/tests` → **7 passed, 3 live subtests passed**.

Owner steps: three, each has an exact Apify Console link or pinned deploy command and usable instruction in `venture.json` / `.actor/README.md`. Account, identity and payout setup are explicit. No extra credential is hidden in code. Actor publication and price selection are gated; the daily source check only updates local health state.

Fixes, prioritized:

1. `ventures/apify-tools/flows/your-step-publish.json` and the publish workflow — keep owner approval on the first three distinct Actor publications, as required by the spec; current gate only names the first.
2. `ventures/apify-tools/src` — extract the Mississippi lookup into the spec's reusable tool template and add a second-engine code/listing review before adding another board; current product covers one board only.

## Warranty registration

Spec: `ventures/SPEC.md:215-233`.

| Field | Status | Finding |
| --- | --- | --- |
| Purpose | partial | Prepares an intake/deadline review queue; does not register units or deliver homeowner certificates. |
| Inputs | partial | Local normalized JSON is accepted; Jobber connector lacks completed-install/homeowner/unit fields and no plate-photo intake is connected. |
| Outputs | partial | A deadline/review queue is produced, but no saved brand confirmation, homeowner certificate or complete unit dashboard is produced. |
| Blocks | partial | Read-only Jobber connector and filer test mock are present; reader/deadline integration is absent in the venture checkout; customer layer/billing is disabled. |
| Loop | partial | Hourly/daily flows exist; photo request is a draft only, brand submission and email do not run. |
| Checks | partial | Duplicate and deadline handling are tested; every brand has `serial_pattern: None`, so real records cannot pass validation. |
| Approval gates | partial | Listing and first-20-email review are named; neither the listing nor email drafts are generated here. |
| Billing | missing | README says billing is not enabled; no test price/customer flow. |
| Edge cases | partial | Region exceptions and uncertainty are handled; portal-break pause/alert and automatic retake/drop notification are not delivered. |

Real data: `ventures/warranty/scripts/warranty.py jobber-preview --as-of 2026-10-10` returned `uncertain — please check`: `jobber_access_token` is not configured. **0 Jobber jobs** were read. No brand portal was accessed; `BRAND_RULES` has no verified serial patterns and portal automation is false for every brand.

Tests: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/warranty/tests` → **15 passed**.

Owner steps: three, but no exact Jobber developer/test-account link or direct Marketplace link is provided in the steps. Brand terms/registration links are listed in README, but the steps do not identify the exact Jobber app page or where to review the first 20 generated emails. Hidden prerequisites in `venture.json` include four Jobber OAuth secrets, five eligible test accounts, source-backed serial formats, a connector returning complete job fields, and reader/deadline block integration. No automated portal/email side effect is enabled, appropriately.

Fixes, prioritized:

1. `ventures/blocks/connectors/clients.py:JobberClient.get_jobs()` — return completed/install date, homeowner and unit fields read-only; the venture's launch gate cannot be met with current connector output.
2. `ventures/warranty/scripts/warranty.py:BRAND_RULES` and `evaluate_install()` — configure only source-backed serial rules after terms review; otherwise keep the affected brand unavailable and provide the exact human fallback path.
3. `ventures/warranty/venture.json` and README — link the Jobber developer/app pages, specify secret-save and connector-check steps, and surface the five-account, reader/deadline and email-review prerequisites in the owner checklist.

## Recall checker

Spec: `ventures/SPEC.md:326-341`.

| Field | Status | Finding |
| --- | --- | --- |
| Purpose | partial | Local lookup exists; release-quality recall identification is not established. |
| Inputs | partial | Local API, CSV and current-tab extension exist; barcode/model intake works, but live feeds are incomplete. |
| Outputs | partial | Match, CSV, API and local HTML pages exist; no public pages are published, correctly. |
| Blocks | partial | Feed/customer blocks are declared; venture-local matching replaces the spec's rules checker, and no acquisition/publication engine is connected. |
| Loop | partial | Nightly refresh/page generation flow exists; full source sync is slow/blocked and model/second-engine matching and wrong-result feedback are absent. |
| Checks | missing | Required 500 recalled + 500 clean benchmark is absent; no measured 1% false-no-match result. One focused vocabulary test fails. |
| Approval gates | partial | First-50 page review flow and first Chrome submission step exist; pages remain local and no hosting action is wired. |
| Billing | partial | Plan ranges and test-only setup are documented; price IDs/API metering are not active. |
| Edge cases | partial | Stale/missing feed produces uncertain; current-tab-only behavior is enforced; similar model cases always return uncertain instead of the specified model/second-engine route. |

Real data: `ventures/blocks/feeds/cli.py sync cpsc_recalls` → **10,047 rows**, no alerts. `sync fsis_recalls` → **0 rows**, HTTP 403. NHTSA full archive sync ran over six minutes without returning output/count and was stopped; FDA openFDA full-partition sync ran over two minutes without output/count and was stopped. One initial FDA attempt shared a temporary SQLite DB with the long NHTSA attempt and failed `database is locked`; a separate-home retry still did not finish. NHTSA and FDA therefore have **no verified count**, not a zero count. No all-source run passed.

Tests: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/recall-checker/tests` → **9 passed, 1 failed**. `test_clean_item_uses_required_source_and_date_vocabulary` expects `no match in ...`; the global venture rule requires `no match found in ...`, and the implementation returns the global-rule form. The branch records this in its claim; do not alter the test to mask the mismatch.

Owner steps: three, but none has an exact link. The README gives local folder/API instructions, but the Chrome Web Store developer page and direct Glacier Secrets route are not linked. Choosing a public host is described in prose, not listed as a step. Reviewing the first 50 pages and submitting the first extension are appropriate owner gates. Test-price setup is plainly described; nightly page generation stays local and does not publish automatically.

Fixes, prioritized:

1. `ventures/blocks/feeds/core.py:_request()` / `fetch_source()` — resolve FSIS's 403 using a supported public endpoint or record it as an unavailable required source; currently every complete recall result remains uncertain.
2. `ventures/blocks/feeds/core.py:_openfda()` and `_nhtsa()` — make refresh bounded and incremental with progress/row counts and per-source timeouts; full syncs did not finish within this review window.
3. `ventures/recall_checker.py:match_item()` — implement the specified fuzzy/local-model then second-engine borderline route, and add the independent 1,000-item labeled benchmark before any accuracy claim or release.
4. `ventures/recall-checker/venture.json` / README — add direct Chrome Web Store and Glacier Secrets links and list public-host selection as an owner step.

## Fixed

### CPSC data prep

- Fixed the reproduced `load_blocks()` class-body `NameError` by importing the block functions under non-shadowed aliases.
- Fixed the direct refresh command's repository import path and its row-count handling (`sync()` returns an integer count).
- Kept the existing exact lawyer-opinion, per-batch importer certification, and first-contract owner gates; surfaced the Stripe test-mode and optional Ollama prerequisites in the existing owner step. CPSC ruleset/field alignment and the shared feed registry/adapter remain with the integrator as requested.
- Acceptance: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/cpsc-prep/tests` → **18 passed**.
- Live source refresh: `GLACIER_HOME=/tmp/glacier-cpsc-X1 /home/glacier/w/glacier-lean/.venv/bin/python ventures/cpsc-prep/scripts/refresh_cpsc_sources.py` → `cpsc_flagged_tariff_codes: 0 rows, HTTP 403`; `cpsc_rule_codes: 0 rows, HTTP 403`; `cpsc_registry_template: 0 rows, HTTP 403`; all three require review. No CPSC feed data was retrieved; the shared feed failure is not represented as a zero-result match.

### Apify data tools

- Reworked the publish approval flow to require a separate owner approval for each of the first three distinct Actor publications, with a different-engine review of each Actor's code and listing before publication.
- Extracted the common Apify lifecycle into `src/actor_template.py` and routed the Mississippi Actor through it. Added a second-board checklist that blocks a new board until source, tests, listing, different-engine review, and owner approval are covered.
- Acceptance: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/apify-tools/tests` → **10 passed, 3 live canary subtests passed**. The live canaries remain the three recorded Mississippi licenses; all matched in this run.

### Warranty registration

- Kept all brands unavailable for automatic serial validation because no source-backed serial pattern is configured. Added the exact human fallback: use the official brand page or contact the brand/dealer, verify manually, and keep the unit on owner review.
- Expanded the existing owner steps with Jobber developer links, the four OAuth secret names, the complete connector field contract, five eligible test accounts, reader/deadline prerequisites, and the first-20-email review gate. The Jobber connector itself is shared work and was not changed.
- Acceptance: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/warranty/tests` → **17 passed**.

### Recall checker

- Added the direct Chrome Web Store developer link, direct Glacier Settings → Secrets route, and a public-host selection step after first-50 page review.
- The FSIS endpoint/other feed refresh work is in the shared feed adapter and remains with the integrator. The fuzzy local-model/second-engine route and 1,000-item benchmark need work outside this venture directory and an independently labeled dataset that was not provided; filed `claim-ph12-12-recall-benchmark-engine` rather than claiming accuracy or release readiness.
- Acceptance: `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/recall-checker/tests` → **10 passed, 1 failed**. The unchanged `test_clean_item_uses_required_source_and_date_vocabulary` expects `no match in ...`, while the global venture vocabulary and implementation require `no match found in ...`; existing claim `claim-ph12-12-recall-output-vocabulary` records the conflict. The judging test was not edited.
