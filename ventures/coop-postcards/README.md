# Co-op claims + street postcards

This venture reads completed Jobber jobs through the same read-only shared `JobberClient` used by warranty, then creates local co-op claim drafts with a source-linked brand record, evidence checklist, and PDF/Markdown output. It does not open a brand portal or file claims. The connected Jobber account name is used as the dealer label; homeowner/client names are not requested or copied into drafts. The postcard flow prepares a local proof for review and never mails it.

The postcard half creates a local proof and distinct landing pages, checks that the sender is clear, checks the recipient against the do-not-mail list, and validates the configured EDDM size/weight fields. Rendering is test-only; no Lob request or mail order is made. The shared mail block's proof PDF remains 6x4, so the generated proof is not yet verified as an EDDM flat print master.

Brand records live in `brand-rules.json`. Carrier, Lennox, Rheem, and Goodman have public program or marketing-support pages, but the current account-specific eligibility, evidence, expense, and claim-deadline terms still require owner confirmation. Trane's public dealer page points to its secure dealer portal for details. All five records therefore say `unverified`; these records are source pointers and checklist starters, not program-rule approvals. If a confirmed program expiry is supplied in the local job detail, the shared deadline tracker registers 60-day and 30-day reminders. Without that owner-confirmed date, the draft says deadline pending and schedules nothing.

`workflow.BRAND_RULES` exposes the five source-linked records by lowercase brand name, with explicit `status` and `verified` aliases for callers. `prepare_claim_draft(job, output_dir=...)` adapts compact Jobber-shaped records into local draft artifacts. It copies only job identifiers and claim inputs; client, property, and raw custom-field payloads are not copied. Missing claim evidence and unverified program terms keep the result not filing-ready. The compact-input acceptance check disputes that readiness result in `DISPUTE.md`.

The shared rules checker and document reader remain available for later evidence review. Current claim drafts do not imply that extracted documents prove eligibility; missing items stay unchecked. No brand credentials or portal access are needed by Glacier, and the claim filing script is now a no-op safety guard. A new Jobber connection has not been made, so live dealer intake remains unverified.

## Your steps

1. Create the Glacier app in [Jobber Developer Center](https://developer.getjobber.com/), request read-only completed-job access, and save the four Jobber OAuth values in Glacier Settings > Secrets.
2. Review the claim drafts and source-linked brand terms, obtain the dealer's authorization, and personally sign/file each brand claim. Choose routes and approve any postcard proof and budget; Glacier only renders local proofs and never mails them.

## Billing and limits

The spec's starting estimate is a 15–25% fee on co-op funds after payout and about $550 per shared-card ad spot, paid at checkout. Pricing and checkout are not activated. If a route card does not fill, the intended policy is refund or roll forward. No paid mailing service is used by this flow.

Dealer and buyer content stays local. Use street-level completed-job addresses only, never homeowner names. Automated 30-day upload deletion is not implemented yet; do not put live customer files into this partial workflow until retention is wired in.

The draft runner is `python3 ventures/coop-postcards/scripts/generate_claim_drafts.py`. It reads completed jobs from Jobber and writes local `.md`, `.pdf`, and `.json` files under `GLACIER_HOME/ventures/coop-postcards/claims/`. For fixture-only offline rendering, pass `--fixture ventures/coop-postcards/fixtures/jobber_completed_job.json --output-dir <local-directory>`. It ignores non-completed jobs. `run_approved_claim.py` intentionally does not submit anything. After personally filing, record the brand response with `scripts/record_claim_outcome.py --claim-id <id> --owner-filed --outcome accepted|rejected --reason "<brand response>"`; a first rejection allows one corrected draft, and a second rejection marks it dropped. Glacier never resubmits.
