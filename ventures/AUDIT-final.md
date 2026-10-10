# final venture integration audit

This is an integration audit, not a launch approval. The installed portfolio validates 31 flows across 11 venture manifests with `ventures/install_all.py --dry-run`. No paid account, external filing, public listing, live mail, or identity check was performed.

## Verified fixes in this integration

- CPSC feed registry now includes the current flagged tariff-code list, rule-code sheet, and registry template. The preparation script maps CPSC’s seven certificate elements to the shared ruleset and registry columns.
- Co-op claim intake reads evidence through the shared reader, checks the shared rules block, and records durable deadline reminders. The stale test now reflects that the shared rules block exists and still rejects a claim without preapproval.
- Postcard proofs use EDDM flat dimensions and enforce the size, thickness, and 3.3 oz limits before a route card can pass.
- The installer validates stable flow IDs, stages venture scripts, and rewrites `{repo}` commands to the installed workspace paths. Re-running installation registers the same flow IDs with PUT.
- Each installed manifest identifies a dry-run flow and has three owner steps with links and written instructions.

## Remaining release gaps

- OSHA has no installed venture or flows. The OSHA card is a claim-only blocker; the build remains unverified.
- The tariff estimator remains on hold pending counsel. No tariff flow was built.
- Jobber, Shopify, and ShipStation credentials are listed in manifests, but the current owner-step form accepts one secret per step. These multi-key connections are not yet requested as a complete one-time set in the needs-you inbox.
- The installed venture manifests have no daily report files, so the venture cards do not show per-venture daily reports. A cross-venture daily digest also needs a verified live walkthrough.
- Scheduled flows have cron expressions, but venture-level missed-run and overlap behavior is not described in the manifests. Confirm the platform scheduler’s policy before relying on unattended production runs.
- Several ventures remain setup or review-only. In particular, warranty’s Jobber connector lacks completed-install intake; external filing, listing, billing, and mailing actions require owner accounts and approvals.
- Daily schedules and draft flows have not yet been exercised end to end against the real Glacier runtime. Screenshots and UI/backend board results will be appended after the final P2/P3 integration and verification run.

## Launch limits

All 11 installed ventures are integrations, not claims of live businesses or validated first-customer results. The owner start table lists the setup action and the actual unlock for each. Keep public listings, external filing, payment, and production mail disabled until their account, legal, and live-data checks pass.
