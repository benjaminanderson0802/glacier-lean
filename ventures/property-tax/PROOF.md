# Property tax appeals proof

## Drift check

- **Checkpoint:** PH12.17, Property tax appeals.
- **Dependencies:** PH5 and PH9 are `in_progress`, not at exit. NORTHSTAR.yaml explicitly says PH12 is owner-approved to start; this card may proceed, while checkpoint completion remains gated on its dependencies.
- **Defining properties and metrics:** P-VERIFY and M-VERIFIED (reader agreement, source citations, independent tests); P-CONTROL (approval-gated handoff and no automated filing); P-USABLE (three plain-language owner steps).
- **Existing tools:** shared feeds, reader, rules, deadlines, customer, mail, filer, and connectors blocks exist. This venture imports the relevant blocks and adds only venture-specific orchestration. No shared block was modified.
- **Acceptance test, written first:** `ventures/property-tax/tests/test_property_tax.py` checks reader citations and recent arm's-length comparables, uncertain-field handling, no-match vocabulary, render-only postcard behavior, and manifest/flow owner-step and approval wiring.

## Checks run

- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests/test_property_tax.py` — **6 passed**.
- `/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only property-tax --dry-run` — **4 flows validated** (`property-tax-refresh-roll`, `property-tax-prepare-packet`, `property-tax-postcard-proof`, `property-tax-upload-retention`).
- Live public source probe through `ventures.blocks.feeds.core`: fetched and normalized one Cook County parcel row with no schema alerts. Exact returned row and source URL: [property-tax-live-source.json](../../evidence/ventures/property-tax-live-source.json). This one-row probe is not the full 50.7M-row roll release check.
- Real-data packet smoke check against that public parcel row: **exit 0**, `uncertain — please check`, with missing notice/comparables listed; `filing_submitted` is false. Exact output: [property-tax-live-case.json](../../evidence/ventures/property-tax-live-case.json).
- Full Cook County feed release check is not established. Existing PH12.5 live evidence records the full roll sync timing out; the feed owner owns that adapter/release check.
- `GLACIER_HOME=/tmp/glacier-property-tax-live-20261010 GLACIER_API=http://127.0.0.1:34335 /home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only property-tax` — **4 flows installed into the real local Glacier backend**; each `PUT /api/environments/<flow>` returned `saved: true` (see `evidence/ventures/property-tax-live-glacier.json`).
- Real packet flow run from Glacier failed before script execution. Run IDs `229a5a729228`, `98e0ea2c5227`, and `a43f0883bc53` show runner root discovery errors; claim `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT` is filed. No successful end-to-end Glacier run or screenshot was produced.

## Owner confirmations

- Confirm Cook County, Illinois as the first packet-only launch county. The Venture Build Spec says Cook County needs an attorney. Current Cook County Assessor appeal rules say no party must be represented by an attorney or agent and permit pro se filing. Keep launch disabled until the owner resolves that difference for this product and confirms the current rules.
- Before Texas work, the owner must confirm eligibility and current consultant registration requirements with TDLR using the link and pre-filled question in `venture.json`. TDLR's current materials describe eligibility, education/exam and association requirements; this is not a generic checkbox.
- Review and approve the exact first postcard design and mailing list and confirm a sender and budget before any external mail. The current flow only renders a local proof.

## Limits

No complete roll sync, customer-authorized notice, real comparable-sales packet, account setup, signature, paid checkout, external postcard, or county submission was run. No live UI screenshot was captured. The shared feed fields currently omit owner mailing addresses and assessed values, so this venture cannot independently identify likely over-assessments or build a public-record recipient list from the current snapshot. Owner/customer-supplied notice and contact records are required until the feed owner adds the necessary public fields. `README.md` explains the customer review and retention steps.
