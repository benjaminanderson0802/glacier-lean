# Apify Store listing: Mississippi Contractor License Status

**Title:** Mississippi Contractor License Status

**Short description:** Check a Mississippi contractor's public license status and expiration from the Mississippi State Board of Contractors.

**Description:** Search Mississippi State Board of Contractors records by license number or business name. Each result includes the board's literal status, expiration date, direct source record, and the time checked. A source outage returns `uncertain — please check`; it is never reported as a clean no-match. The board cautions that circumstances may change after publication, so verify directly before relying on a result. This independent Actor is not affiliated with or endorsed by the board and does not provide a legal conclusion.

**Search terms:** Mississippi contractor license; MSBOC license lookup; contractor status; contractor expiration; contractor verification

**Input:** See `.actor/input_schema.json`. Provide one license number or business name, or a batch of up to 100 queries. Name searches return at most 10 matches. The source query and detail requests are rate-limited to at least one per second.

**Output:** One dataset record per readable match, with `outcome`, `verification_state`, `license_number`, `business_name`, literal `status`, `expiration_date`, `source_url`, and UTC `checked_at`. A readable no-match is dated. An unreadable source is `uncertain — please check` with `verification_state: unverifiable`.

**Source note:** Mississippi State Board of Contractors public lookup: https://search.msboc.us/ConsolidatedSearch.cfm. Board record pages include this disclosure: “circumstances may have changed since the time of publication.” No affiliation or endorsement is implied.

**Pricing:** Pay per event, $0.02 per completed lookup. Platform usage included. Source outages are not charged. Set a $2.00 maximum total charge per run and disable the automatic `apify-default-dataset-item` charge event.

**Support:** Use the Apify Actor Issues tab for technical problems. For official interpretation or a current decision, contact the Mississippi State Board of Contractors.
