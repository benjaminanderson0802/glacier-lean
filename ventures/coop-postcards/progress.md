# Progress — Co-op claims and street postcards

Venture release status is **ready for owner setup and review**. PH12.13 remains `todo` in NORTHSTAR until dependencies PH5 and PH9 reach exit; this card does not mark the checkpoint done.

The claim flow reads completed-job metadata through the shared read-only Jobber client. Its venture-specific query requests job identifiers, status/title, completion time, and source URL only; it does not request client, property, or custom-field data. It creates local Markdown/PDF claim drafts, source-linked brand records, evidence checklists, and 60/30-day reminders only when a confirmed expiry is supplied. Claim drafts stay not filing-ready when required evidence is absent or brand terms remain unverified.

The postcard flow checks sender, suppression, route, and EDDM size/weight fields, then renders distinct local landing pages and a two-sided 11.5 × 6.25 inch USPS EDDM Retail review PDF. The USPS size thresholds and boundary scenarios are captured in `evidence/eddm-usps-benchmark.json`. This is a render-only review proof, not a production master. No Lob request, order, publication, payment, or mailing occurred.

Both flows completed through the real local Glacier engine with fixture data. Run IDs, node states, outputs, and errors are in `evidence/live-flow-runs.json`; copied fixture artifacts are in `evidence/live-flow-output/`. The co-op test command passed 15 tests. All five configured brand links resolved over HTTPS with HTTP 200, while program eligibility and account-specific rules remain explicitly unverified.

The sandbox has no Jobber OAuth secret mapping, so connected-account behavior remains unverified. The README includes the exact one-command owner check after the owner saves the four Jobber values in Glacier Settings → Secrets. The remaining owner step also covers confirming current program rules, signing/filing claims, choosing any price or budget, and approving the exact proof before any mailing. No owner-only action was automated.
