# Mississippi Contractor License Status

Check Mississippi contractor licenses using the public Mississippi State Board of Contractors lookup. Search by license number or business name, and receive the board's status, expiration date, direct record link, and UTC check time. This Actor returns the published record without making a legal conclusion.

## Store listing

**Short description**

Check a Mississippi contractor's public license status and expiration from the Mississippi State Board of Contractors.

**Description**

Search Mississippi State Board of Contractors records by license number or business name. Each result includes the board's literal status, expiration date, direct source record, and the time checked. A source outage returns `uncertain — please check`; it is never reported as a clean no-match. The board cautions that circumstances may change after publication, so verify directly before relying on a result. This independent Actor is not affiliated with or endorsed by the board and does not provide a legal conclusion.

**Search terms**

Mississippi contractor license; MSBOC license lookup; contractor status; contractor expiration; contractor verification

**Pricing**

Pay per event: **$0.02 per completed lookup**, including a readable no-match result. A source outage is not charged. Platform usage is included. Suggested maximum run charge: **$2.00** (100 input searches). Configure the `license-lookup` event in Apify Console before publishing, and disable Apify's automatic `apify-default-dataset-item` event so one lookup is billed once.

## Your steps

1. **Your step: Set up the Apify developer and payout account.** Open [Apify account settings](https://console.apify.com/account/integrations) and complete the account and payout setup in your own name. Identity verification and payout information stay with the owner.
2. **Your step: Log in and deploy the Actor.** From the repository root, paste `cd ventures/apify-tools && npm exec --yes --package=apify-cli@1.10.0 -- apify login && npm exec --yes --package=apify-cli@1.10.0 -- apify push`. The pinned Apify CLI prompts the owner to log in, then deploys this Actor.
3. **Your step: Approve each of the first three distinct Actor publications.** Run Glacier's publication approval separately for each new Actor. Record its unique name, independently review its code and listing, confirm its event price, included platform usage, run limit and disabled automatic `apify-default-dataset-item` charge, then publish it yourself in the [Apify Console](https://console.apify.com/actors). An earlier approval never covers another Actor. The current Mississippi Actor is the only prepared listing; do not publish a future listing until its code and listing have been independently reviewed.

## Source and limits

- Source: [Mississippi State Board of Contractors public lookup](https://search.msboc.us/ConsolidatedSearch.cfm). The board's record pages caution that circumstances may change after publication; verify directly before relying on a result.
- At most one request per second; name searches return at most 10 records; each run accepts at most 100 searches.
- Status and expiration are shown as published. A readable empty search says `no match found in Mississippi State Board of Contractors public contractor search as of [date]`; an unavailable source returns `uncertain — please check` with `verification_state: unverifiable`.
- This independent Actor is not affiliated with or endorsed by the Mississippi State Board of Contractors.
