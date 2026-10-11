# Co-op claims + street postcards

This venture pairs a dealer-authorized brand co-op claim workflow with neighborhood postcard proofs. It is aimed at dealer year-end budgets: the postcard preparation flow opens on November 1, and the brand claim intake tracks 60-day and 30-day reminders from each program expiry date.

The postcard half can create a local 6x4 proof and distinct landing pages, check that the sender is clear, check the recipient against the do-not-mail list, and use Lob only with a `test_` key. A live mail order is not available in these flows. The current shared mail block renders 6x4 cards; the spec's USPS EDDM flat-size check still needs a compatible print format before the postcard product can launch.

The shared reader, rules, and deadline packages are now present, but this venture does not yet call the reader or deadline APIs for claim documents and reminders. Do not treat a claim as filing-ready until the venture wires those checks into intake. The portal filer is prepared for use, but no real brand account or portal is configured. The Jobber connector can read jobs but does not provide a dealer-facing Jobber app screen yet.

## Your steps

1. Before intake, create the Glacier app in [Jobber Developer Center](https://developer.getjobber.com/), request read-only access, and save the credentials in Glacier Settings > Secrets. Use a real callback only after Glacier has a deployed callback URL.
2. Before the first claim per brand, review that brand's program rules and confirm the customer's authorization. The customer signs and submits anything sent to a government agency.
3. Before the first November campaign, choose the towns/routes, approve the exact proof and budget, configure Lob test mode, and confirm a printer and post-office drop that meet the EDDM flat specs.

## Billing and limits

The spec's starting estimate is a 15–25% fee on co-op funds after payout and about $550 per shared-card ad spot, paid at checkout. Pricing and checkout are not activated in this partial build. If a route card does not fill, the intended policy is refund or roll forward. Lob is paid software and remains in test mode only until the owner configures credentials and approves a live mail plan.

Dealer and buyer content stays local. Use street-level completed-job addresses only, never homeowner names. Automated 30-day upload deletion is not implemented yet; do not put live customer files into this partial workflow until retention is wired in.

Rejected claims have one documented correction attempt. After a customer reports a first rejection, record it with `scripts/record_claim_outcome.py --claim-id <id> --outcome rejected --reason "<brand reason>"`; correct the packet and rerun it through the Glacier approval. Record the second result the same way. A second rejection marks the claim dropped, and the workflow will refuse a third filing attempt. Accepted outcomes close the claim attempt record.
