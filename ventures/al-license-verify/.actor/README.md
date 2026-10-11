# Alabama Contractor Roster Check

## What this Actor does

Check whether a license number or exact business name appears in a dated Alabama contractor roster CSV that **you upload and are authorized to use**. The Actor returns the source fields, source URL, snapshot date, and check time in a dataset that you can export as JSON or CSV or connect through the Apify API. It does not visit the Alabama board website, download a roster, or decide whether a contractor is legally qualified.

Use it for a small subcontractor roster review, vendor onboarding cross-check, or repeat comparison against a roster your organization already has permission to use. The example prefill is synthetic. Replace it with your own file and queries.

## How to run it

1. Upload a CSV roster using the **User-supplied roster CSV** field.
2. Enter the date represented by that file and the source URL for reference. The URL is stored as metadata and is never fetched.
3. Enter one or more license numbers or exact business names. A query must contain exactly one of those fields. The batch limit is 100.
4. Start the Actor and inspect the `outcome`, `verification_state`, source, and check time in the output dataset.
5. Confirm important results with the relevant board before relying on them.

The input accepts common column headers for license number, business name, status, expiration, specialty, and address. CSV rows are matched exactly after basic punctuation and case normalization. Duplicate matches, conflicting fields, missing comparison columns, or a snapshot more than 365 days old return `uncertain — please check`. A readable exact absence returns `no match found in supplied Alabama roster as of [date]`.

## Pricing

The proposed Store price is **$0.001 per verified exact match**. A successful match is charged only after its result row is written. Readable no-match results, stale or conflicting records, upload failures, and uncertain results are not charged. There is no start fee or automatic dataset-item charge. A 100-query batch therefore has at most $0.10 in custom match events. Confirm the final price, platform usage setting, and run limit in the Store pricing panel before publication.

Apify provides run monitoring, dataset storage and export, API access, and scheduling for repeated checks. Standard Apify account charges and storage retention settings still apply to your account.

## Example input

```json
{
  "roster_file": "<upload a CSV in Apify Console>",
  "roster_as_of": "2026-10-11",
  "source_url": "https://genconbd.alabama.gov/",
  "queries": [{"license_number": "AL-EXAMPLE-1042"}]
}
```

The example query and output values are fabricated test fixtures, not a live board record. The Actor cannot validate the source URL, CSV ownership, or a contractor's identity.

## Limits and privacy

This Actor reads only the uploaded Apify file and stores the resulting rows in the run dataset. Do not upload data you are not authorized to process. The customer controls input and dataset retention in Apify. A result reflects a point-in-time file and is not a certified report, legal conclusion, insurance check, or guarantee of current status. No board affiliation or endorsement is claimed.

For support, use the Apify Issues tab or contact `{{BUSINESS_EMAIL}}`. Include the run ID and a redacted example; do not email a full roster or confidential data.
