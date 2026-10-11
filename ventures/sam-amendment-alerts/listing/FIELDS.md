# Apify Store fields to paste

Prepared for the Apify Console Publishing tab. Follow the current Console form and official references in `APIFY-REVIEW-CHECKLIST.md` if its fields change.

## Display information

- **Name:** SAM.gov Amendment and Deadline Change Alerts
- **Actor name / slug:** `sam-opportunity-change-alerts`
- **Short description:** Compare complete SAM.gov Opportunities API snapshots for your NAICS codes. Get dated rows for newly observed notices, version/amendment changes, or response-deadline changes. Bring your own encrypted SAM.gov API key.
- **SEO title:** SAM.gov Amendment and Deadline Change Alerts
- **SEO description:** Track SAM.gov opportunity changes by NAICS. Compare complete API snapshots and receive dated new-notice, amendment, and response-deadline rows.
- **Long description / Store README:** paste [`README.md`](README.md)
- **Categories:** Business (`BUSINESS`), Lead generation (`LEAD_GENERATION`), and Automation (`AUTOMATION`); select the matching categories offered in the Console.
- **Search terms:** SAM.gov amendment alert, SAM.gov deadline change, federal opportunity monitoring, NAICS opportunity monitor, SAM.gov API, contract notice changes
- **Actor logo:** upload [`logo.png`](logo.png) (512 × 512); [`logo.svg`](logo.svg) is the editable source.
- **Support contact:** `{{BUSINESS_EMAIL}}`
- **Sample output:** use [`sample-output.json`](sample-output.json); all opportunity data in the example is illustrative fixture data.
- **Output schema:** use [`../.actor/dataset_schema.json`](../.actor/dataset_schema.json)
- **Input schema:** use [`../.actor/input_schema.json`](../.actor/input_schema.json)
- **Permissions:** choose limited permissions; the Actor only needs to call the public SAM.gov Opportunities API and read/write its named key-value-store baseline plus its run dataset. It does not need browser, proxy, or account access.
- **Screenshots:** not required by the official publishing checklist. Input/output JSON examples are in the README. Do not upload screenshots of the Apify Console unless the Console later requires them.

## Privacy and support

- **Privacy policy:** paste [`PRIVACY.md`](PRIVACY.md)
- **Support text:** “For help with a run, open an issue in the Actor's Apify Issues tab or email `{{BUSINESS_EMAIL}}`. Include the run ID and a redacted input example; never send your SAM.gov API key.”

## Monetization

- **Model:** Pay per event
- **Event:** `opportunity-change` / “Verified opportunity change”
- **Recommended price:** USD $0.001 per verified changed notice row
- **Charge basis:** only after each verified new-notice/amendment/deadline-change row has been written successfully
- **No charge:** first baseline, no-change result, uncertain row, incomplete snapshot, API outage, quota/rate-limit response
- **Platform usage:** included in event pricing; verify the Console's usage handling and run cap before approval
- **Automatic events:** disable `apify-actor-start` and `apify-default-dataset-item`; do not double-charge rows
- **Run cap:** choose a user-visible max charge consistent with the expected notices; the Actor's data bounds are 2,000 records per run and 20 NAICS codes.
