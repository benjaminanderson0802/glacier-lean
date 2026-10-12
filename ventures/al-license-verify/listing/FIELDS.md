# Apify Store fields to paste

Prepared for the Apify Console Publishing tab. Store fields can change; follow the current Console form and the linked official publishing docs in `APIFY-REVIEW-CHECKLIST.md`.

## Display information

- **Name:** Alabama Contractor Roster Check
- **Actor name / slug:** `alabama-contractor-roster-check`
- **Short description:** Check exact contractor license numbers or business names against a dated Alabama roster CSV you are authorized to use. No board scraping; no-match and uncertain results are free.
- **SEO title:** Alabama Contractor License Roster CSV Checker
- **SEO description:** Check exact Alabama contractor license numbers against an authorized dated roster CSV. Get source dates and status fields; no board scraping or legal conclusions.
- **Long description / Store README:** paste [`README.md`](README.md)
- **Categories:** Business (`BUSINESS`) and Automation (`AUTOMATION`); select the corresponding categories offered in the Console.
- **Search terms:** Alabama contractor license, contractor roster, license status, expiration date, CSV lookup, subcontractor verification
- **Actor logo:** upload [`logo.png`](logo.png) (512 × 512); [`logo.svg`](logo.svg) is the editable source.
- **Support contact:** `{{BUSINESS_EMAIL}}`
- **Sample output:** use [`sample-output.json`](sample-output.json); the values are synthetic and demonstrate schema only.
- **Output schema:** use [`../.actor/dataset_schema.json`](../.actor/dataset_schema.json)
- **Input schema:** use [`../.actor/input_schema.json`](../.actor/input_schema.json)
- **Permissions:** choose the least-privileged option that permits this Actor to read the user's Apify file upload and write its own run dataset. No proxy, browser, or external network permission is needed by the Actor.
- **Screenshots:** not required by the official publishing checklist. Input/output JSON examples are included in the README. Do not upload screenshots of the Apify Console unless the Console later requires them.

## Privacy and support

- **Privacy policy:** paste [`PRIVACY.md`](PRIVACY.md)
- **Support text:** “For help with a run, open an issue in the Actor's Apify Issues tab or email `{{BUSINESS_EMAIL}}`. Include the run ID and a redacted input example; never send a roster containing personal or confidential information.”

## Monetization

- **Model:** Pay per event
- **Event:** `license-lookup` / “Verified roster match”
- **Recommended price:** USD $0.001 per verified exact match
- **Charge basis:** only after a `match` row has been written successfully
- **No charge:** readable no-match, stale snapshot, ambiguous/conflicting data, malformed input, upload outage, source uncertainty
- **Platform usage:** included in the event price; verify the Console's platform usage and run-limit behavior before approval
- **Automatic events:** disable `apify-actor-start` and `apify-default-dataset-item`; do not double-charge rows
- **Run cap:** $0.10 for the 100-query maximum
