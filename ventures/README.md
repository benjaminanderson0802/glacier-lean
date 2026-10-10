# Ventures integration index

This index follows [SPEC.md](SPEC.md), the owner-approved source of truth. “Integrated” means a manifest and runnable flow are present; it does not mean the venture is launch-ready. Wave 2 integration includes B1, V-CPSC, V-COOP, and the ventures already present on `origin/glacier-final`.

Independent findings for this wave are recorded in [AUDIT-wave2.md](AUDIT-wave2.md); unresolved integration gaps are tracked in `vault/claims/`.

## Shared blocks

| Block | Status here | Release check | Owner steps |
| --- | --- | --- | --- |
| Document reader | Integrated; benchmark release gate pending | `blocks/reader/CHECK.md` | Configure local Ollama and model for the two-engine public-sample benchmark; no customer files are needed for the fixture check. |
| Rules checker | Integrated; fixture release check pending rerun | `blocks/rules/CHECK.md` | No owner step for the local ruleset fixtures. A `pass` is a cited field check, not a legal determination. |
| Portal filer | Integrated; mock acceptance check | `blocks/filer/CHECK.md` | Use only a customer-authorized domain and credentials; obtain customer approval for each submission. Real portals remain unconfigured. |
| Government data feed | Integrated; real-source release gate pending | `blocks/feeds/CHECK.md` | None for public-source sync. A source alert or unavailable source blocks that source's release. |
| Deadline tracker | Integrated; fixture release check pending rerun | `blocks/deadlines/CHECK.md` | None for the calendar fixtures. Customer-specific deadlines need source rules. |
| Customer layer | Integrated; recorded-response check | `blocks/customer/CHECK.md` | Save a Stripe test key and test price in Glacier Secrets only if exercising optional test checkout. Owner signs customer contracts and approves refunds. |
| Acquisition engines (mail) | Integrated; render-only and test-mode check | `blocks/mail/CHECK.md` | Keep the initial mail path render-only. A real Lob test requires an owner-configured `test_` key; the owner approves first designs and any paid mail order. |
| Platform connectors | Integrated; fixture check | `blocks/connectors/CHECK.md` | Create platform accounts, complete identity/app setup, save credentials in Glacier Secrets, and run the read-only connection command. No real account check has been run. |

Package imports are rooted at `ventures.blocks`; all eight contract modules are now present. A passing fixture suite does not imply live platform credentials or real-source release evidence.

## Ventures

Owner steps below are taken from the approval gates, build queue, and setup requirements in SPEC.md. Any public launch, account signup, identity check, legal decision, spend, or government filing remains an owner/customer action. No venture below has an integrated manifest and runnable flow in this branch.

| Venture | Status | Exact owner steps before/at launch |
| --- | --- | --- |
| CPSC data prep | Integrated; local acceptance and install checks available; real feed + second-engine batch proof pending | Obtain the trade lawyer’s written opinion that the broker flat-fee model is permitted; review and sign the first broker contract; review every extracted batch field, resolve uncertain values, and certify the upload as importer or licensed broker. The customer/importer or broker submits to CPSC. |
| Apify data tools | Not integrated; branch not final | Create/sign in to the Apify account and complete payout setup; create and least-privilege the dedicated token, then save it in Glacier Secrets; choose three terms-permitted public license canaries; review and publish the first three actors. |
| Warranty registration | Not integrated; branch not final | Create/configure the Jobber developer app and test account; save OAuth credentials in Glacier Secrets and run its read-only connection check; review the marketplace listing and submit it after five eligible test accounts; review the first 20 homeowner emails. |
| Recall checker | Not integrated | Review and submit the first Chrome Web Store listing; review the first 50 recall pages. The extension must stay limited to the page the user opened. |
| Co-op claims | Integrated; prior real-runtime approval smoke is recorded, fresh install proof pending; one stale test assumption and shared-block production gaps remain | Review the first claim for each brand; authorize each customer claim and sign/submit any government filing where applicable. |
| Street postcards | Integrated; local proof and test-mode flow; not launch-ready because EDDM flat-size/weight proof is missing | Choose the first towns/routes; approve the first card before print; complete the Lob account and printer/post-office setup; approve each buyer proof where its checkout terms require approval. |
| Freight claims | Not integrated | Complete ShipStation partner/app access; review the first ten claims; the shipper decides whether to accept any settlement/full release. |
| FDA cosmetics listing tool | Not integrated | Create the Shopify Partner app/account and development store; request only `read_products`; complete app review and submit the first listing. The brand confirms product/ingredient data; Glacier does not submit FDA filings. |
| OSHA filing | Not integrated | Approve the first postcard design; review the first five submissions; the establishment’s executive signs the 300A certification and the customer submits through their own OSHA account (or explicitly authorizes a delegate). |
| Property tax appeals | Not integrated | Select the initial counties and mail design; obtain Texas consultant registration before Texas filings; the property owner reviews/signs and submits each appeal. |
| Utility audits | Not integrated | Choose the launch state and utility tariff; approve the first customer-facing offer. The customer confirms account data and approves any utility authorization or external submission. |
| DIBBS government supply | Not integrated | Complete SAM.gov and CAGE registration; approve each quote/order and sign all government representations. Glacier may prepare bid packets but the owner/customer submits. |
| Carpenter’s goods | Integrated; fixture tests and manifest install check; real runtime path still needs verification | Agree commission terms with the carpenter in writing; approve the first product listing and any paid production/order. |
| Tariff estimator | On hold by owner’s instruction; not built | Do not build or launch until the owner’s trade lawyer approves the flat-fee model and confirms open deadlines; importer or licensed broker files. |

## Out of scope

These five SPEC cuts are excluded and have no venture manifests: motel dynamic pricing, unclaimed property recovery, Whop clipping, truck dispatch, and restaurant delivery refunds.

## Installer and manifest contract

`venture.schema.json` is the single manifest schema. `install_all.py --dry-run` validates each manifest, flow ID, schedule declaration, and node type against Glacier’s shared node catalog. It exits with an error when no manifest exists; it will not report an empty installation as success. `python -m pytest -q ventures/tests` checks the schema contract and empty-install behavior.
