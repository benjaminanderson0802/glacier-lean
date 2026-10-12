# Independent acceptance findings — job-closeout

The acceptance checks are independent of the generator and its existing tests.
Run date: 2026-10-10.
Source field provenance is in [ACCEPTANCE.md](ACCEPTANCE.md). The sole live
canary ran once with `RUN_LIVE=1`: Jobber's official developer page returned
HTTP 200 and contained `completedAt`. It used no account credentials or data.
The captured command output is in
[`tests/acceptance/evidence/live-canary.log`](tests/acceptance/evidence/live-canary.log).

Offline run: `~/w/glacier-lean/.venv/bin/python -m pytest -q -k 'not live_official_document_contract' tests/acceptance` — **6 failed, 10 passed, 1 deselected**. Failures are left in place:

- `test_pdf_preserves_unicode_customer_name`: PDF rendering replaces the Chinese character in `José 李` (the Markdown path preserves the fixture's text).
- `test_malformed_completion_not_asserted_as_fact`: `completedAt: "not-a-date"` is emitted as a date fact.
- `test_partial_or_failed_source_never_delivers_packet`: an unfinished page is accepted and creates a packet; GraphQL partial errors are ignored; null outage/rate-limit data escapes as an unhandled `TypeError` rather than a controlled uncertain result. The test cases fail separately for these cases.

Prospect review: all three rows provide first-party business websites and a
published office phone, with no personal email or personal contact. They are
not contacted. The URLs are business-owned sources, not independent licensing
or trade-directory records; current HVAC activity is plausible but Jobber use,
record-export permission and buyer interest remain explicitly unverified. The
owner's pilot notes correctly require manual owner review and approval before
any invoice; no test sends, publishes, or charges.

## Windows portability follow-up — 2026-10-11

The current acceptance and unit checks passed in the combined requested-suite
run; the earlier PDF Unicode, malformed completion, and partial-source failures
recorded above were not reproduced in this checkout. Text assertions now specify
UTF-8, path checks use POSIX shell form, and the offline guard refuses ordinary
loopback and non-loopback connects while narrowly allowing asyncio's own
loopback `socketpair()` call.
