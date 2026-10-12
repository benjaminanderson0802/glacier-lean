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

## Windows portability follow-up — 2026-10-11

The acceptance and unit checks now read text as UTF-8, compare shell command
paths in POSIX form, and guard both `connect` and `connect_ex`. The guard only
permits a loopback connect when the Python stack shows both `socketpair()` and
`asyncio`; separate checks assert ordinary loopback and non-loopback connects
are refused. On the project interpreter, the combined requested suites report
**6 failed, 143 passed, 5 skipped**. All six failures remain in the SAM product
checks: the UI notice link is replaced with the API self link, and incomplete
pagination, missing retrieval metadata, malformed rows, missing deadlines, and
conflicting duplicate IDs do not return the required refusal/uncertainty. No
product code was changed.

## Card drift check

This work advances PH12.22 under the owner-approved venture wave. PH5 and PH9
remain `in_progress`, so no roadmap checkpoint status is changed. It serves
P-PORTABLE and M-PORTABLE by making the independent checks consistent across
Windows and Linux. Existing Python standard-library path, encoding, socket, and
pytest facilities cover the need; no dependency or tool was added. Acceptance is
the combined six-venture/mail pytest command recorded in the card report, with
all portability checks passing and the six SAM product defects retained as
failures.
