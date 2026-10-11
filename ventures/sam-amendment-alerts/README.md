# SAM.gov Amendment and Deadline Change Alerts

## What this Actor does

Track new SAM.gov notices and observed amendment/version or response-deadline changes for one or more NAICS codes. The Actor calls the official SAM.gov Opportunities API v2 with **your own free API key**, compares each complete result with the previous complete snapshot for the same code set, and writes one dated row for each detected change. The API key field is encrypted by Apify and the key is not copied to output or saved comparison data.

Use this Actor to keep a low-cost change feed for federal opportunities you already monitor. The first successful run saves a baseline and returns a baseline notice. Later runs can be scheduled in Apify; each successful run updates the saved snapshot. Different NAICS-code sets have separate baselines.

## How to run it

1. Obtain your own free SAM.gov public API key and enter it in the secret key field. Do not paste it in the README, a support request, or dataset.
2. Enter one or more 2–6 digit NAICS codes. The prefilled example is `423840` (industrial supplies merchant wholesalers).
3. Run the Actor once to save a baseline. This run is not billed.
4. Schedule or run the Actor again later to check for changes. Review each source-linked row and verify the live notice and deadline on SAM.gov.

The Actor reads bounded pages (up to 20 pages, 100 records each by default; 2,000 total records per run maximum) and refuses to save a partial snapshot. A quota error, outage, malformed response, or incomplete capture produces an uncertain row without billing and leaves the previous baseline unchanged. A no-change run writes a dated no-change row without billing.

The saved baseline remains in the named Apify key-value store `sam-amendment-alerts-state` until you remove that store in your Apify account. Removing it starts a new baseline on the next successful run.

## Pricing

The proposed Store price is **$0.001 per verified changed notice row**: a new notice, amendment/version change, or response-deadline change. The charge happens only after the matching output row is successfully written. The initial baseline, no-change, uncertain, incomplete, quota-limited, and outage results are not charged. The proposed price is USD $1 per 1,000 changes; confirm the final price and platform-usage setting in the Store panel. The recommendation is to include platform usage in this event price, so customers are not billed separate platform usage for no-change or failed runs; the publisher still bears those underlying platform costs.

Apify gives you scheduled runs, monitoring, API access, datasets, and exports. You can download the result dataset or connect it to your own workflow through the Apify API.

## Example input

```json
{
  "api_key": "<enter your own key in the encrypted secret field>",
  "naics_codes": ["423840"]
}
```

## Example output

The included sample is generated from illustrative fixtures, not an active SAM.gov solicitation. A result row includes event type, notice ID, title, watched NAICS, previous/current deadline or version when present, the public notice URL, and the UTC snapshot time.

## Limits and privacy

This Actor reports only changes observed between the saved baseline and latest complete API snapshot. It does not reconstruct amendments published before your first run, determine bid eligibility, predict awards, submit bids, or provide procurement advice. Verify all details on the live SAM.gov notice. It is not a U.S. government service and is not affiliated with SAM.gov.

Your secret key is sent only to the official SAM.gov Opportunities API for the requested read-only search. The Actor stores public notice snapshots in an Apify named key-value store for later comparison; the key itself is not included. For support, use the Actor's Apify Issues tab or email `{{BUSINESS_EMAIL}}`; never send an API key. A full privacy policy is prepared in the adjacent `listing/PRIVACY.md` file for the Store policy field.
