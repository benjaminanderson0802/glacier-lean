# Apify Store listing: Louisiana Contractor License Status

**Title:** Louisiana Contractor License Status

**Short description:** Check a Louisiana contractor's public license status and expiration from the Louisiana State Licensing Board for Contractors.

**Description:** Search Louisiana State Licensing Board for Contractors records by license number or company name. Each result includes the license type, literal board status, effective and expiration dates, direct source record, and the time checked. A source outage returns `uncertain — please check`; it is never reported as a clean no-match. Verify directly with the board before relying on a point-in-time status. This independent Actor is not affiliated with or endorsed by the board and does not provide a legal conclusion.

**Search terms:** Louisiana contractor license; LSLBC license lookup; contractor status; contractor expiration; contractor verification

**Input:** See `.actor/input_schema.json`. Provide one license number or company-name substring, or a batch of up to 100 queries. Company searches require at least 3 characters and return at most 10 matching licenses. Every source search and detail request is rate-limited to at least one per second.

**Output:** One dataset record per matched license, with `outcome`, `verification_state`, `license_number`, `business_name`, `license_type`, literal `status`, `effective_date`, `expiration_date`, `source_url`, and UTC `checked_at`. A readable no-match is dated. An unreadable source is `uncertain — please check` with `verification_state: unverifiable`.

**Source note:** Louisiana State Licensing Board for Contractors search: https://lslbc.louisiana.gov/contractor-search/. Public portal: https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber. No affiliation or endorsement is implied.

**Pricing:** Pay per event, $0.02 per completed lookup. Platform usage included. Source outages are not charged. Set a $2.00 maximum total charge per run and disable the automatic `apify-default-dataset-item` charge event.

**Review gate:** The distinct-engine code and listing review has no blocking findings; this listing still requires its own owner approval in Glacier before publication.

**Support:** Use the Apify Actor Issues tab for technical problems. For official interpretation or current status, contact the Louisiana State Licensing Board for Contractors.
