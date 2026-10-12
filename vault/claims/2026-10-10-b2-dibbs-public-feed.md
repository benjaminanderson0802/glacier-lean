---
id: CLM-2026-10-10-B2-DIBBS-PUBLIC-FEED
filed_by: B2
run_id: null
node_id: null
checkpoint: PH12.5
kind: policy
summary: DIBBS solicitation pages require a consent step before public records are exposed
evidence: "Live probe of the configured DIBBS homepage, /rfq/, /rfq/rfqsearch.aspx, /Downloads/RFQ/, /Downloads/RFQ/W/, and a public RFQ detail URL returned only the DIBBS warning/consent shell (about 11 KB each); the homepage exposed no solicitation rows. No consent was submitted, and no login or account was used."
attempts_made: 1
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

## Blocker

The requested public DIBBS feed is not available to this unauthenticated adapter. The official host serves its DoD warning/consent page for the public homepage, RFQ search and download paths. The current adapter correctly returns no records and an alert rather than treating the consent page as solicitation data.

## Reproduction

- `ventures.blocks.feeds.core._dibbs(registry()["dla_dibbs"])` returned zero rows and the alert `No solicitation rows were found on the public page; DIBBS may have changed its page format or requires its public search form.`
- Additional read-only probes of `/rfq/`, `/rfq/rfqsearch.aspx`, `/Downloads/RFQ/`, `/Downloads/RFQ/W/` and a public `rfqrec.aspx` URL all returned the same warning/consent shell.

No acknowledgement, account creation, credentials or bid submission was attempted. Under the card's hard rule, this worker cannot accept the warning/consent step. Please route to the owner/integrator to identify an approved public export or authorize a permitted access method. Until resolved, the PH12.5 feeds release check must remain blocked for DIBBS; the other source checks may proceed independently.

## Alternatives checked

1. Official public solicitations landing page.
2. Official RFQ directory/search, including the RFQ search and download paths.

Both present the same consent shell to this adapter, so neither provides parseable public rows without crossing the consent gate.
