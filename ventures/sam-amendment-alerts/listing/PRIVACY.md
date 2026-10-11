# Privacy policy — SAM.gov Amendment and Deadline Change Alerts

**Contact:** `{{BUSINESS_EMAIL}}`

This Actor receives the NAICS codes you select and your own SAM.gov public API key. The key field is marked as a secret in the Actor input schema; Apify encrypts saved secret input values and makes them available to the Actor during that run. The Actor sends the key to the official SAM.gov Opportunities API endpoint as required for an API request. SAM.gov therefore receives the API request and key. The Actor does not write the key to its dataset, saved comparison snapshots, status messages, or error text.

The Actor retrieves public opportunity data, compares it with the previous complete snapshot for the same NAICS-code set, and writes result rows to the run's Apify dataset. It stores the latest complete snapshot in the named Apify key-value store `sam-amendment-alerts-state` so later runs can compare against it. Snapshot data contains public notices and timestamps, not the API key. Different NAICS-code sets use separate baseline records. Named stores persist until you delete them; the customer controls access to the Apify account, dataset, and named storage and can delete the named store to clear all saved baselines.

Do not share your API key with support. If a run fails, share only the run ID and a redacted input example. Apify's privacy, account-security, and data-retention terms apply to data stored by the Apify platform. The Actor does not send data to an email service, CRM, or other third party.

Results describe changes observed only between complete snapshots. SAM.gov's current response may not provide historical amendments from before the first snapshot. A changed deadline must be verified on the live notice. The Actor is not affiliated with or endorsed by the U.S. government, does not assess bid eligibility, and does not predict awards.

Contact `{{BUSINESS_EMAIL}}` for privacy questions or support. This draft must be reviewed and the contact placeholder replaced before publication.
