# Ventures integration index

This index follows [SPEC.md](SPEC.md), the owner-approved source of truth. “Not integrated” means no manifest and runnable flow are present in this integration branch. The only finished branches in `I1-branches.txt` were B3, B4, and B5; CPSC, Apify, and platform branches were not in that list and were not merged.

## Shared blocks

| Block | Status here | Release check | Owner steps |
| --- | --- | --- | --- |
| Document reader | Not integrated | No block or `CHECK.md` present | None available until the block is built. |
| Rules checker | Not integrated | No block or `CHECK.md` present | None available until the block is built. |
| Portal filer | Merged from B4; acceptance check needs rerun | `blocks/filer/CHECK.md` | Use only a customer-authorized domain and credentials; obtain customer approval for each submission. Real portals remain unconfigured. |
| Government data feed | Not integrated | No block or `CHECK.md` present | None available until the block is built. |
| Deadline tracker | Not integrated | No block or `CHECK.md` present | None available until the block is built. |
| Customer layer | Merged from B3; recorded-response check available | `blocks/customer/CHECK.md` | Save a Stripe test key and test price in Glacier Secrets only if exercising the optional test checkout. Owner signs customer contracts and approves refunds. |
| Acquisition engines (mail) | Merged from B4; acceptance check needs rerun | `blocks/mail/CHECK.md` | Keep the initial mail path render-only. A real Lob test requires the owner to configure a `test_` key; the owner approves first designs and any paid mail order. |
| Platform connectors | Merged from B5; fixture checks available | `blocks/connectors/CHECK.md` | Create platform accounts, complete identity/app setup, save credentials in Glacier Secrets, and run the read-only connection command. No real account check has been run. |

Package imports are rooted at `ventures.blocks`; the current modules are `customer`, `filer`, `mail`, and `connectors`. The other four contracts remain unimplemented.

## Ventures

Owner steps below are taken from the approval gates, build queue, and setup requirements in SPEC.md. Any public launch, account signup, identity check, legal decision, spend, or government filing remains an owner/customer action. No venture below has an integrated manifest and runnable flow in this branch.

| Venture | Status | Exact owner steps before/at launch |
| --- | --- | --- |
| CPSC data prep | Not integrated; CPSC branch not in finished list | Obtain the trade lawyer’s written opinion that the broker flat-fee model is permitted; review and sign the first broker contract; review every extracted batch field, resolve uncertain values, and certify the upload as importer or licensed broker. The customer/importer or broker submits to CPSC. |
| Apify data tools | Not integrated; no Apify venture branch in finished list | Create/sign in to the Apify account and complete payout setup; create and least-privilege the dedicated token, then save it in Glacier Secrets; choose three terms-permitted public license canaries; review and publish the first three actors. |
| Warranty registration | Not integrated | Create/configure the Jobber developer app and test account; save OAuth credentials in Glacier Secrets and run its read-only connection check; review the marketplace listing and submit it after five eligible test accounts; review the first 20 homeowner emails. |
| Recall checker | Not integrated | Review and submit the first Chrome Web Store listing; review the first 50 recall pages. The extension must stay limited to the page the user opened. |
| Co-op claims | Not integrated | Review the first claim for each brand; authorize each customer claim and sign/submit any government filing where applicable. |
| Street postcards | Not integrated | Choose the first towns/routes; approve the first card before print; complete the Lob account and printer/post-office setup; approve each buyer proof where its checkout terms require approval. |
| Freight claims | Not integrated | Complete ShipStation partner/app access; review the first ten claims; the shipper decides whether to accept any settlement/full release. |
| FDA cosmetics listing tool | Not integrated | Create the Shopify Partner app/account and development store; request only `read_products`; complete app review and submit the first listing. The brand confirms product/ingredient data; Glacier does not submit FDA filings. |
| OSHA filing | Not integrated | Approve the first postcard design; review the first five submissions; the establishment’s executive signs the 300A certification and the customer submits through their own OSHA account (or explicitly authorizes a delegate). |
| Property tax appeals | Not integrated | Select the initial counties and mail design; obtain Texas consultant registration before Texas filings; the property owner reviews/signs and submits each appeal. |
| Utility audits | Not integrated | Choose the launch state and utility tariff; approve the first customer-facing offer. The customer confirms account data and approves any utility authorization or external submission. |
| DIBBS government supply | Not integrated | Complete SAM.gov and CAGE registration; approve each quote/order and sign all government representations. Glacier may prepare bid packets but the owner/customer submits. |
| Carpenter’s goods | Not integrated | Agree commission terms with the carpenter in writing; approve the first product listing and any paid production/order. |
| Tariff estimator | On hold by owner’s instruction; not built | Do not build or launch until the owner’s trade lawyer approves the flat-fee model and confirms open deadlines; importer or licensed broker files. |

## Out of scope

These five SPEC cuts are excluded and have no venture manifests: motel dynamic pricing, unclaimed property recovery, Whop clipping, truck dispatch, and restaurant delivery refunds.

## Installer and manifest contract

`venture.schema.json` is the single manifest schema. `install_all.py --dry-run` validates each manifest, flow ID, schedule declaration, and node type against Glacier’s shared node catalog. It exits with an error when no manifest exists; it will not report an empty installation as success. `python -m pytest -q ventures/tests` checks the schema contract and empty-install behavior.
