# A-CASH evidence and limitations

Card date: October 10, 2026 America/Chicago. Public API acquisition: October 11 at 02:51 UTC, still October 10 in Alabama. Branch: `card/gf-A-CASH`. All changed files are under `ventures/`. No phase/checkpoint status changed.

## Inventory and primary-source audit

`rg --files --hidden -g actor.json ventures` finds exactly four Actor definitions, all without a `readme` override. Apify's documented preference is `.actor/README.md`; two existing preferred files were polished and two were added. Their root developer READMEs and older store_listing/PILOT pricing hypotheses are not deployment configuration. [PRICING](../../apify-tools/PRICING.md) explicitly identifies the new recommendations and old Alabama $0.05 hypothesis.

The public API JSON files preserve the request URL, retrieval timestamp and complete response (up to the requested 100 results each). They are a reproducible snapshot, not an exhaustive Store census. The CPSC query's unrelated results are deliberately retained as evidence that broad search counts are misleading. Selected listing prices and all associated events were copied from `currentPricingInfo`, never guessed from Store marketing labels. Private account status and current profitability remain unverified.

Original prospect lists had 15 closeout, 22 Alabama bid and 16 SAM rows, sourced from association directories or old SBA profiles. This card replaces them with three deliberately chosen contacts per offer, each on the company's own official site. No minimum count was requested. We prefer a small verified start over retaining unverified personal-looking email seeds. Contacts are business contact routes, not opt-ins, verified purchasers or proof of software use. Older README descriptions of the directory seed lists are historical; the updated CSV/PILOT is the current outreach material.

| Offer | Official source checked | What is supported |
|---|---|---|
| Closeout | https://acbyluquire.com/ | Montgomery HVAC/plumbing business; office phone 334-264-9666. No email verified. |
| Closeout | https://834hans.com/contact-us/ | Montgomery HVAC business; 334-834-HANS (4267). Search-index official page available; direct fetch intermittently failed. Use phone only, recheck before call. |
| Closeout | https://edwardsplumbing.com/ | Office 334-834-6120, Mon–Fri 7–4; separate emergency number excluded. No email verified. |
| Alabama bid | https://personsservices.com/contact/ | Corporate office@personsservices.com and 251-660-0132; use office for routing rather than a bid-submission inbox. |
| Alabama bid | https://www.rogerswillard.com/contact | info@rogerswillard.com, 251-479-2675. Old /contact/ path was unreliable; followed current site's Contact link. |
| Alabama bid | https://www.rjbaggett.com/office-location-mailing-address/ | Bids/RFQ phone 251-473-3290 ext. 140; obscured email deliberately not inferred. |
| SAM | https://atekdistribution.com/contact-us/ | info@atekdistribution.com, 952-254-1205. Government/GSA navigation supports a fit hypothesis, not current bidding activity. |
| SAM | https://www.burgooncompany.com/contactus | office@burgooncompany.com, 409-766-1900; government-procurement language. |
| SAM | https://www.pcindustrialsupplies.com/contact_us | sales@pcindustrialsupplies.com, 734-426-1400. No current NAICS/registration claim from an old SBA profile. |

No unrelated Luquire advertising agency contact was included. Roby site's 403 and C. Thornton source failures were not bypassed. Rogers & Willard's third-party project portals were not entered. No sales form, appointment request, account, email, bid or private Actor was accessed or submitted.

## Document review

Initial-email word counts, including subject and footer but excluding section title: closeout 133, Alabama bid 136, SAM 134. Follow-ups: 84, 87, 85. Final sender/address substitution must keep each email under 150 words; there is room for an ordinary postal address. Templates intentionally retain the unknown owner's address placeholder; a draft with that placeholder must not be sent. An asynchronous owner question requested business address/payment/operating status; none was supplied during preparation.

The original safeguards remain: closeout first-five review, Alabama three-firm/sample gate, SAM two-buyer/live-data gate. No false testimonials, fabricated purchase records or synthetic opportunities presented as live. Examples in the four Actor READMEs are either labeled synthetic/illustrative or explicitly dated recorded output. Recall source statuses use the implementation's `as_of` field. Event conditions are derived from `src/actor_template.py` and Alabama `src/__main__.py`, including billable uncertainty and outage exclusions.

All 12 original manifest ventures, four pilots, the extra Actor routes, both co-op business lines, the tariff hold and absent FBA kit are explicitly accounted for in FASTEST-MONEY. Estimates distinguish orders/earnings from settled cash, explain their assumptions and do not assert a measured conversion rate.

## Checks and environment limits

Exact per-venture command: `~/w/glacier-lean/.venv/bin/python -m pytest ventures/<name> -q`, separate process per venture to avoid generic `src` module collisions. Results are in `pytest-<name>.log`; no tests or ACCEPTANCE.md were edited.

Required screen static checks were attempted from `glacier/web`:

- `node e2e/theme_lint.mjs`: passed, 52 files (`theme-lint.log`).
- `npx tsc -b`: failed because the existing node_modules environment lacks TypeScript; npx fetched the unrelated `tsc@2.0.4` package into its cache, which reports it is not the TypeScript compiler (`tsc.log`). No repo dependency was added or changed. Do not repeat this command until the pinned dependencies are restored.
- `node scripts/check-i18n.mjs --fail`: could not run, missing `typescript` (`i18n.log`).

This is an environment blocker outside A-CASH's venture-document paths, not a product failure caused by these documents. Integrator needs to restore the pinned frontend dependencies in an isolated/shared-environment-safe way and rerun TypeScript/i18n checks. No attempt was made to alter another worker's node_modules link, package files or acceptance checks. This out-of-lane issue is reported here for routing; a canonical `vault/claims/` entry would require a path outside this card's deliverable lane.

No screen or backend behavior was changed, so there are no related UI e2e/backend test files to run. No PH12 checkpoint is being accepted as done. Accordingly the post-checkpoint core/live-worker board is not invoked for this content card: the inspected `setup/run_core_tests.sh` reinstalls shared dependencies and deletes a fixed `/tmp/e2edata`, while `live_codex_check.sh` writes to a fixed localhost backend. Those are integrator checkpoint checks, not suitable read-only validation of sales documents beside other workers. Existing runtime evidence is cited with its original limits.

## Drift / anti-pattern review

See [pre-edit plan](../A-CASH-PLAN.md) for the five drift-check answers and acceptance rubric. Sales material is the owner's explicit deliverable, so this is not a report substituted for an assigned software feature. No governance/infrastructure code, acceptance changes or unsupported checkpoint status was introduced. Found misleading-readiness risks were corrected in the new handoff: synthetic samples, missing live SAM capture, absent Chrome package, payout delay and unproven demand. No NORTHSTAR amendment is proposed. `docs/AMENDMENTS.md` remains outside this card's paths.

## Final venture-suite results

| Suite | Result |
|---|---|
| apify-tools | 12 passed, 1 skipped, 3 subtests passed in 8.28s |
| apify-tools-louisiana | 9 passed, 3 subtests passed in 8.45s |
| recall-actor | 13 passed, 2 skipped, 3 subtests passed in 6.58s |
| al-license-verify | 9 passed in 7.87s |
| job-closeout | 3 passed in 3.19s |
| al-bid-triage | 4 passed in 1.40s |
| sam-amendment-alerts | 4 passed in 0.56s |
| tests | 21 passed in 5.30s |

Total: 75 passed, 3 skipped, 9 subtests passed. All eight commands exited 0. Skipped checks are opt-in live checks; no new live recall accuracy claim is made. `git diff --check` passed after normalizing generated CSV line endings.
