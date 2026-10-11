# Acceptance — V-RECALLFIX

1. Treat openFDA HTTP 404 with `error.code == NOT_FOUND` as a successful empty result, equivalent to `NO_RECORDS_FOUND`; malformed 404 responses remain unavailable.
2. Search CPSC with bounded separate UPC, `ProductName`, and `RecallTitle` queries; shorten trailing generic product words and try apostrophe variants. Never use the ignored `Title` parameter or combine literal filters that suppress valid matches.
3. Cap CPSC requests at six per lookup, rate-limit them, union and deduplicate records by RecallID, and leave brand/model/name filtering to conservative matching.
4. Report `uncertain` when all CPSC requests fail, and a successful empty source result when requests succeed with no hits.
5. Push each complete result record (`outcome`, `message`, `query`, `matches`, `sources_checked`, `checked_at`) and expose those fields in the dataset schema.
6. With `RECALL_LIVE=1`, the Rock 'n Play canary must return a CPSC match linked to cpsc.gov or saferproducts.gov; the check is skipped by default.
7. Keep `PROOF.md` explicit about fixture-only checks versus live canaries and do not claim a live result unless the opt-in canary actually ran.
