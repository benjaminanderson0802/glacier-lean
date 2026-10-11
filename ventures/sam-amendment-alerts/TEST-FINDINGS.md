# Independent acceptance findings — sam-amendment-alerts

The acceptance checks are independent of the snapshot comparator and its
existing tests. Run date: 2026-10-10. Field provenance is in [ACCEPTANCE.md](ACCEPTANCE.md). The one
live canary reached GSA's official API documentation (HTTP 200; marker
`opportunitiesData`); it did not call SAM with an API key. Output is captured
in [`tests/acceptance/evidence/live-canary.log`](tests/acceptance/evidence/live-canary.log).

Offline run: `~/w/glacier-lean/.venv/bin/python -m pytest -q -k 'not live_official_document_contract' tests/acceptance` — **6 failed, 9 passed, 1 deselected**. Failures are left in place:

- The generated event links to the API `links[].href` rather than the supplied `uiLink`; GSA documents that the API link requires a key and its UI link may require a SAM.gov role. The test therefore checks we preserve the supplied UI link, not that it is public without login.
- The comparator does not detect incomplete pagination (`totalRecords` exceeds captured rows), absent local retrieval metadata, or malformed rows, and does not surface missing deadlines as `uncertain - please check`.
- Conflicting duplicate `noticeId` rows are silently overwritten in the snapshot map.

Prospect review: all three rows use first-party business contact pages and
published general business inboxes/phones. No person-specific emails are
listed, and all are marked not contacted. The linked pages are official
business-controlled sources; they do not establish current federal bidding,
NAICS qualification or active buyer interest. The pilot correctly makes a
working authorized feed, two accepted snapshots and two explicit buyer
agreements prerequisites to manual invoicing. There is no live source fetch or
payment action in this kit.
