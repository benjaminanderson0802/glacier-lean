# Louisiana Contractor License Status

## Store listing

**Short description**

Check a Louisiana contractor's public license status and expiration from the Louisiana State Licensing Board for Contractors.

**Description**

Search Louisiana State Licensing Board for Contractors records by license number or company name. Each result includes the license type, literal board status, effective and expiration dates, direct source record, and the time checked. A source outage returns `uncertain — please check`; it is never reported as a clean no-match. Verify directly with the board before relying on a point-in-time status. This independent Actor is not affiliated with or endorsed by the board and does not provide a legal conclusion.

**Search terms**

Louisiana contractor license; LSLBC license lookup; contractor status; contractor expiration; contractor verification

**Pricing**

Pay per event: **$0.02 per completed lookup**. A readable no-match is billed; a source outage is not. Platform usage is included. Suggested maximum run charge: **$2.00** (100 input searches). Configure the `license-lookup` event in Apify Console before publishing and disable the automatic `apify-default-dataset-item` event.

## Owner steps

1. **Your step: Set up the Apify account and deploy this Actor.** Use the official Apify CLI, from the repository root: `cd ventures/apify-tools-louisiana && npm exec --yes --package=apify-cli@1.10.0 -- apify push`.
2. **Your step: Approve and publish this distinct listing.** Review the no-blocking different-engine review in `../REVIEW.md`, then use the separate Glacier publication approval and publish it yourself in Apify Console. The Mississippi approval cannot be reused.

## Source and limitations

- Official search page: https://lslbc.louisiana.gov/contractor-search/
- Public search portal: https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber
- At most one request per second; company-name searches require 3 or more characters; name searches return at most 10 licenses; each run accepts at most 100 searches.
- A readable empty search says `no match found in Louisiana State Licensing Board for Contractors public search as of [date]`. Source or parse failures return `uncertain — please check` with `verification_state: unverifiable`.
- The Actor is not affiliated with or endorsed by the Louisiana State Licensing Board for Contractors.
