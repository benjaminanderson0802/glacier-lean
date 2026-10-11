# Ventures integration index

This index follows [SPEC.md](SPEC.md), the owner-approved source of truth. “Integrated” means a manifest and runnable flow are present; it does not mean the venture is launch-ready. Wave 6 integration includes all 12 in-scope ventures.

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

The current owner-facing steps and direct links are maintained in [OWNER-START-HERE.md](OWNER-START-HERE.md). “Ready” means the prepared workflow has no known build blocker and awaits owner/customer setup or review. “Blocked” identifies a release gate or implementation/evidence gap. “Live” requires public operating evidence; none of the ventures currently qualifies. An account connection, local run, fixture pass, or synthetic record alone is not a live launch.

| Venture | Status | Current evidence or release gate |
| --- | --- | --- |
| Apify data tools — Mississippi contractor licenses | Ready | Three live source canaries and a verified real-Glacier daily canary; Actor is built, payout verification and listing price remain. |
| Carpenter’s goods | Blocked | Focused fixtures pass; real Glacier command run previously failed at the unresolved `{repo}` working-directory issue; no owner sales records. |
| Co-op claims + street postcards | Blocked | Local acceptance and a synthetic render-only run; claim reader/deadline wiring and USPS EDDM size proof remain. Jobber test app is connected, but live dealer intake is not verified. |
| CPSC data prep | Blocked | Fixture suite and flow validation pass; source IDs/rules integration and real public-source release checks remain. |
| DIBBS government supply | Blocked | Fixture suite passes; SAM.gov was submitted 2026-10-10. An IRS check and CAGE code are pending before DIBBS registration; the public DIBBS source currently returns a DoD warning page and no rows. |
| FDA cosmetics listing preparation | Blocked | Fixture suite and synthetic SPL schema check pass; Shopify development store is connected, but the reader-contract claim, no live product/label record, and no FDA acceptance remain. |
| Freight claims | Blocked | Local fixture packet and suite pass; no live ShipStation/customer run, and the shared filer tests lack the Playwright module. |
| OSHA filing | Blocked | Official feed parsed 400,288 rows and synthetic draft checks pass; complete Jobber field contract and customer-record run remain. |
| Property tax appeals | Blocked | One live parcel row and an uncertain local packet were checked; county-rule discrepancy, complete roll, and successful real-Glacier run remain. |
| Recall checker | Blocked | Recall Actor fixed and rebuilt on Apify; a live Rock 'n Play check returns a match. Rename and pricing remain, as does the required labeled 500-recalled/500-clean benchmark. Chrome Web Store developer account is registered, but no listing is submitted. |
| Utility audits | Blocked | Synthetic input and fixture tests pass; Indiana launch and pricing/legal basis need owner confirmation, and no customer bills were available. |
| Warranty registration | Blocked | Fixture checks and a synthetic real-Glacier deadline review pass; connected Jobber test app lacks a verified full field contract, and serial rules/email drafts remain. |
| Tariff estimator | Blocked | Explicit owner hold; no flow is installed pending counsel approval. |

All venture suites were run in isolation on 2026-10-10 because a single root pytest collection collides on generic `src` and `scripts` imports. Per-directory outcomes and causes for the remaining red checks are recorded in [OWNER-GUIDE-TESTS.md](OWNER-GUIDE-TESTS.md). Do not treat the integration count or fixture passes as release evidence for a gate listed above.

## Out of scope

These five SPEC cuts are excluded and have no venture manifests: motel dynamic pricing, unclaimed property recovery, Whop clipping, truck dispatch, and restaurant delivery refunds.

## Installer and manifest contract

`venture.schema.json` is the single manifest schema. `install_all.py --dry-run` validates each manifest, flow ID, schedule declaration, and node type against Glacier’s shared node catalog. It exits with an error when no manifest exists; it will not report an empty installation as success. `python -m pytest -q ventures/tests` checks the schema contract and empty-install behavior.
