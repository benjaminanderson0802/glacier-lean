# Independent venture review — R2

Scope: PH12.22 review of `coop-postcards`, `freight-claims`, `fda-cosmetics`, and OSHA filing. Venture branches were inspected in isolated worktrees. A direct no-ff merge conflicted in shared registries/contracts; it was aborted without resolving or changing venture code. FDA and freight use the I3 integrated snapshot; co-op is present in the current integration; the OSHA branch contains only a capability-gap report.

## Co-op claims + street postcards

Spec source: `ventures/SPEC.md`, “Co-op claims and street postcards.” References below are under `ventures/coop-postcards/` in the integrated tree.

| Spec field | Status | Evidence |
|---|---|---|
| Purpose | partial | Claim readiness and postcard proof scaffold in `workflow.py`; README says no live mail, claims not filing-ready, and pricing/checkout inactive. |
| Inputs | partial | `intake.schema.json`, `scripts/check_claim_intake.py`, `scripts/check_route_card.py`; no Jobber dealer-facing intake, live brand rules, invoices, or portal connection. |
| Outputs | partial | `flows/coop-claim-readiness.json`, `flows/street-postcard-proof.json`, `workflow.py`; renders proof/landing pages, but no live EDDM order, claim confirmation, or available/claimed/paid balance. |
| Blocks | partial | `workflow.py` checks rule input; reader and deadline APIs are not wired in; Jobber app screen, production mail format, printer, and real brand portal are absent (`README.md`). |
| Loop | partial | Flows cover readiness/proof and `claim_reminder_dates`; no automated rule ingestion, claim tracking/payout invoice, route send, delivery, or 30/60-day scheduled reminders. |
| Checks | partial | Preapproval/evidence/sender/suppression checks in `workflow.py`; 6x4 rendering is not checked against EDDM flat-size/weight requirements. |
| Approval gates | partial | Claim flow and mail script require Glacier approval IDs (`scripts/run_approved_claim.py`, `scripts/send_postcard.py`); no verified first-claim-per-brand workflow against real rules. |
| Billing | missing | Only estimated rates in README; checkout and pricing are not activated. |
| Edge cases | partial | Missing evidence and preapproval produce uncertainty; no one-corrected-resubmit-then-drop behavior or operational handling of a rejected claim. |

**Real data:** No public-source script is present for dealer locators or brand programs. No real Jobber, brand portal, or Lob data was queried; real records/claims/mail count: **0**. The postcard script is limited to Lob `test_` mode; this is not live-source evidence.

**Tests:** `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/coop-postcards/tests` — **1 failed, 6 passed**. `test_claim_requires_preapproval_and_shared_rules_pass_before_filing` expects `uncertain` because its comment assumes no shared rules block; the integrated tree now has that block and returns `pass`.

**Owner steps:** README has 3 numbered steps. Step 1 links Jobber Developer Center and gives access/secret instructions. Step 2 gives brand-rule and authorization instructions but no link to a brand’s rules/portal (must be selected per brand). Step 3 is several setup/approval actions, without a printer link. Hidden/unlisted: configure real callback after deployment; no live Lob order is available; a compliant EDDM printer/drop is a launch dependency; retention is not implemented. Any live mailing and money spend must stay gated; current test-only gate is appropriate.

## Freight claims

Spec source: `ventures/SPEC.md`, “Freight claims.” Evidence under `ventures/freight-claims/` in the I3 integrated snapshot.

| Spec field | Status | Evidence |
|---|---|---|
| Purpose | partial | `scripts/claims.py` prepares customer-reviewed packet drafts; it does not file claims or invoice recovery. |
| Inputs | partial | Local incoming JSON and attachment paths documented in `README.md`; tracking can use ShipStation only after explicit secret + enable file. No customer-facing upload link. |
| Outputs | partial | Packet, email draft, and `freight-record-carrier-receipt` flow; customer must send the claim and supply confirmation. No live filing or status page. |
| Blocks | partial | Shared reader, deadlines, connector, filer draft, and signature block are used; ShipStation is read-only/disabled by default, and no customer billing integration is active (`README.md`, `scripts/claims.py`). |
| Loop | partial | Six flows in `flows/`; customer manually supplies documents and carrier receipt. No automatic end-to-end exception watch until the owner enables quota-bearing tracking. |
| Checks | partial | `build_claim_packet` limits amounts to confirmed damaged-item invoice lines, requires docs, gates insurance and carrier terms; no real carrier claim or independently validated carrier-liability rule. |
| Approval gates | partial | README calls for listing review and first ten packet reviews; customer retains sending and settlement decisions. Listing/packet review is not yet proven as an enforced Glacier owner gate. |
| Billing | partial | Contingency amount is an invoice draft only; no checkout, payment link, or charge. |
| Edge cases | partial | Missing documents/uncertainty/insurance are surfaced; no implemented settlement-with-full-release accept/decline flow was found. |

**Real data:** `claims.py watch` has no usable live ShipStation data without an owner-provided key and opt-in file; no account was configured, so live shipment/claim count: **0**. The recorded packet demo uses synthetic fixture data and produces one draft packet; it is not a real-source count. Carrier terms in that fixture are synthetic.

**Tests:** `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests` — **14 passed**.

**Owner steps:** README lists 3. Step 1 lacks a direct ShipStation developer link and bundles connection plus listing review; exact quota opt-in instructions exist only in the longer README body. Step 2 is clear. Step 3 bundles authorization, review, sending, receipt reporting, recovery, and invoice approval. The customer must provide files in a local folder, confirmed receipt, and recovery data; no upload link exists. Tracking calls can consume plan quota, and the explicit enable file is an appropriate approval gate. Customer sending/signing/settlement remains gated.

## FDA cosmetics listing

Spec source: `ventures/SPEC.md`, “FDA cosmetics listing tool.” Evidence under `ventures/fda-cosmetics/` in the I3 integrated snapshot.

| Spec field | Status | Evidence |
|---|---|---|
| Purpose | partial | `scripts/listing_prep.py` generates a customer-submitted SPL ZIP; no live listing service or portal validation. |
| Inputs | partial | Shopify connector supplies catalog titles/IDs; `brand-details.json` must manually supply ingredients, facility, responsible person, and confirmations (`README.md`). |
| Outputs | partial | Local SPL ZIP/checklist and reminder registration in `scripts/listing_prep.py`; no FDA response email workflow is demonstrated, and no FDA acceptance is verified. |
| Blocks | partial | Reader/rules/deadline and Shopify connector are called; customer billing and app listing are absent. Ingredients are not in the connector and require manual source details. |
| Loop | partial | Product read, customer review, generation and local validation exist; FDA upload and response forwarding/parsing remain customer actions, with no app-store workflow. |
| Checks | partial | Uncertain/missing fields block ZIP generation; tests do not establish FDA acceptance. Proof describes only SPL XSD validation for synthetic data; no live response. |
| Approval gates | partial | Customer confirms every value and submits; Shopify app review is a launch dependency, not an operational approval flow. |
| Billing | missing | README says product-count subscription is planned and billing disabled. |
| Edge cases | partial | Uncertain ingredients/facilities block generation; small-business exemption checklist is manual. No handling of an actual FDA rejection was evidenced. |

**Real data:** No Shopify credentials/catalog or brand label were available; real products/listings: **0**. No FDA portal request/submission was made. Public FDA references are in `PROOF.md`, but no venture script fetched a live source. The generated test data is synthetic.

**Tests:** `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests` — **4 failed, 3 passed**. The valid-listing, Shopify merge, and deadline tests unexpectedly return uncertain/not-ready; the uncertainty test also misses `ingredients` because missing `label.pdf` is reported first as a missing source document. The failure is in the current integrated snapshot.

**Owner steps:** README has 3 steps. No exact Shopify app or Cosmetics Direct links are supplied. Step 1 combines app creation, scopes, secret setup, and manual product/facility data; step 2 is clear; step 3 bundles signature, portal upload, and app review. Missing from the numbered list: FDA response forwarding and annual/120-day deadline monitoring. The customer signing/submission gate is correct. No live app listing is ready to review.

## OSHA filing

Spec source: `ventures/SPEC.md`, “OSHA filing.” `ventures/osha-filing/` and its tests/scripts are **absent** from the integrated tree and the OSHA card branch. `ventures/README.md` marks OSHA “Not integrated.” The branch’s `ventures/AUDIT-wave1.md` reports a missing shared capability; no venture is implemented.

| Spec field | Status | Evidence |
|---|---|---|
| Purpose | missing | No OSHA venture files. |
| Inputs | partial | Shared `ventures/blocks/feeds/core.py` has an OSHA ITA source adapter; no customer injury log, hours, headcount, or certification intake. |
| Outputs | missing | No 300A generator, submission confirmation, posting copy, or reminder flow. |
| Blocks | partial | Shared OSHA public feed and generic mail/filer/deadline blocks exist; no venture wiring, form rules, or customer layer integration. |
| Loop | missing | No refresh, selection, postcard, intake, certification, filing, or annual reminder flow. |
| Checks | missing | No totals/plausibility/signature/confirmation checks. |
| Approval gates | missing | README describes intended first postcard/first five reviews and customer submission, but no operational gate exists. |
| Billing | missing | No venture billing implementation. |
| Edge cases | missing | No delegate failure/refund or post-March waitlist handling. |

**Real data:** Tried `/home/glacier/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync osha_ita` against the official OSHA ITA download page. The call produced no count after 90 seconds and was interrupted while normalizing downloaded rows in `ventures/blocks/feeds/core.py`; **count unavailable**, source not confirmed broken, feed pipeline did not finish. No OSHA filing source/customer data was queried. A retry should first bound the feed size/row processing rather than repeat the unbounded sync.

**Tests:** `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests` — no tests ran; directory does not exist.

**Owner steps:** `ventures/README.md` lists intended actions but offers no exact links or runnable instructions. No functioning “your steps” path exists. Executive certification, OSHA account/delegate setup, and customer submission must remain explicit customer gates; spending/publication gates are not implemented either.

## Prioritized fixes

1. **OSHA venture (one worker):** add `ventures/osha-filing/venture.json`, flows, scripts, tests, and a three-step README. Wire and bound `ventures/blocks/feeds/core.py::_osha`/`normalize_rows`; record live row count and add canaries before claiming a real-data pass. Without this, PH12.16 is wholly unimplemented.
2. **FDA tests and validation (one worker):** fix `ventures/fda-cosmetics/tests/test_fda_cosmetics.py` fixture setup and `scripts/listing_prep.py::_reader_review`/`prepare_listing` so test fixture documents exist and successful confirmed payloads produce the expected packet; validate against FDA’s current published SPL rules/schema, then retain customer submission gate. Current suite is 4/7 failing.
3. **Co-op integration checks (one worker):** update `ventures/coop-postcards/tests/test_workflow.py::test_claim_requires_preapproval_and_shared_rules_pass_before_filing` to assert the integrated rules behavior without editing away the check; wire reader/deadline use in claim flow and add tests for the spec’s corrected-resubmit rule. Keep live mail disabled until the renderer supports USPS EDDM dimensions and the first-send approval is enforced.
4. **Freight onboarding and settlement path (one worker):** add an exact ShipStation link/quota setup and customer upload path in `ventures/freight-claims/README.md`/flows; implement enforced first-ten review and full-release settlement accept/decline gates in the freight flows/scripts. Keep tracking opt-in and customer-controlled sending.
5. **FDA owner onboarding (one worker):** add exact links and divide product-detail, FDA portal submission, response-forwarding, and deadline tasks in `ventures/fda-cosmetics/README.md`; connect retention and customer-layer billing before commercial launch.

## Fixed

Drift check for this card: PH12.22 and venture checkpoints PH12.13–PH12.16. PH12 depends on PH5 and PH9, which are not at exit; the owner-approved PH12 wave-6 card authorizes these venture fixes to proceed but does not authorize marking checkpoints done. The changes serve P-VERIFY and P-CONTROL, with M-VERIFIED and M-AUDIT as the relevant evidence measures. Existing free/shared reader, rules, feed, deadline, connector, and filer blocks were reused where applicable; custom code is venture-specific glue. Acceptance checks were written or reproduced before each behavior fix, and no judging test was edited to weaken its assertions.

1. **OSHA filing and bounded public feed.** Added a customer-controlled OSHA 300A review worksheet workflow, intake checks, deadline reminders, three owner steps, a submission approval, and focused tests. The OSHA feed now caps the HTML page at 5 MB, the CSV at 150 MB, and parsing at 1,000,000 rows; it stops with a clear error if a cap is exceeded. Feed adapter tests cover current-link discovery, row count, and byte limits. Shared feed change was isolated in commit `d1a2713` with its adapter test. No OSHA account, customer injury data, postcard, payment, certification, or filing was touched.
   - `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests` — **5 passed**. `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only osha-filing --dry-run` — **2 flows validated**.
   - `GLACIER_HOME=/tmp/glacier-osha-x2 ~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync osha_ita` — **400,288 rows**, `changed: false`, **0 alerts** from the current official OSHA ITA Summary Data CSV (`https://www.osha.gov/itadata`).

2. **FDA fixture, reader failure handling, and SPL validation.** Test fixtures now create the label file required by production path checks. `_reader_review` turns malformed document-reader exceptions into an uncertain customer-review result instead of crashing. Fully confirmed payloads produce the expected local ZIP while preserving the customer signing/submission gate.
   - `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests` — **8 passed**. `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — **2 flows validated**.
   - A generated synthetic SPL was checked with `lxml.etree.XMLSchema` against FDA's published `SPL.xsd` from its current [SPL resources page](https://www.fda.gov/industry/fda-data-standards-advisory-board/structured-product-labeling-resources) (FDA currently links the 2016 schema package): **`FDA SPL XSD valid: True`**. This proves XML structure only; Cosmetics Direct's own validation and actual FDA acceptance were not tested.

3. **Co-op integrated rules check and rejected-claim retry.** The integrated-rules assertion in `test_claim_requires_preapproval_and_shared_rules_pass_before_filing` was already corrected in this integrated tree; it now asserts pass for valid evidence and fail when required preapproval is missing. Added a persisted claim-attempt state machine and outcome recorder: a first rejection permits one corrected resubmit, a second rejection drops the claim, and accepted claims close their attempt record. Each submit still requires Glacier approval. Per the card instruction, reader/deadline wiring and USPS EDDM dimensions/weight are left to the integrator.
   - `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/coop-postcards/tests` — **9 passed**. `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only coop-postcards --dry-run` — **2 flows validated**.

4. **Freight onboarding, first-ten review, and settlement decision.** README and the intake folder now give the exact local upload path for claim JSON and source documents; ShipStation authentication and current usage-limit links are supplied, with the existing request ceiling made explicit (up to 20 shipment-page requests and 100 tracking requests per daily run). Added a persistent local approval ledger for the first ten distinct packets, a one-packet-per-approval flow gate, and a settlement flow that requires the shipper's explicit accept/decline choice for a full-release offer. Acceptance closes the claim; decline keeps it active. The shipper continues to control sending and settlement decisions. The intake remains a local on-device handoff; there is no hosted upload link.
   - `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests` — **17 passed**. `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only freight-claims --dry-run` — **7 flows validated**.

5. **FDA owner onboarding.** Reworked the three owner steps around Shopify product-detail setup, FDA Cosmetics Direct submission and response forwarding, and 120-day/annual listing deadline review. Added direct Shopify, FDA form, portal, and FDA guide links plus the local response intake path. README and manifest state that retention deletion and customer-layer billing are launch dependencies, not working features.
   - `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests` — **8 passed**. `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — **2 flows validated**.
   - FDA references checked against [Cosmetics Direct](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/cosmetics-direct), [Form FDA 5067](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing), and the February 2026 [Cosmetics Direct user guide](https://direct.fda.gov/apex/f?p=100:103:::::P103_GUIDE:26). The guide states an initial listing is due within 120 days after first marketing and updates are annual.

Anti-pattern review: no governance layer or unrelated platform feature was added. The feed's previously unbounded processing was bounded before retrying; the successful source count is recorded above. No checkpoint status or evidence field in NORTHSTAR was changed. Commercial launch dependencies remain the shared customer layer/retention and any real customer accounts or source data, which were unavailable in this card.
