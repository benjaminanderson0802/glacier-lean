# Independent acceptance findings — al-bid-triage

The acceptance checks are independent of the CSV triager and its existing
tests. Run date: 2026-10-10. Field provenance is in [ACCEPTANCE.md](ACCEPTANCE.md): Alabama Builds
provides human-readable notices, while the tested CSV is explicitly a local
customer/transcriber mapping. The single live canary reached the official
Alabama Builds listing (HTTP 200; marker `Alabama Builds`), without collection
or extraction. Output is in
[`tests/acceptance/evidence/live-canary.log`](tests/acceptance/evidence/live-canary.log).

Offline run: `~/w/glacier-lean/.venv/bin/python -m pytest -q -k 'not live_official_document_contract' tests/acceptance` — **4 failed, 11 passed, 1 deselected**. Failures are left in place:

- Missing bid date, issuer, and pre-bid details are printed as “Not supplied”
  or a weaker check notice instead of the required `uncertain - please check`
  language.
- Conflicting duplicate notice numbers with different deadlines are silently
  reduced to the first row.

Prospect review: three first-party company contact pages/phones are listed;
two rows use role-based office inboxes, the third directs the owner to a Bids/RFQ
office line. No person-specific contact is included and all are marked not
contacted. The sources establish the businesses, not their interest in Mobile
or Baldwin public bids. No automated notice collection, bid submission, email,
publication or payment is performed.

## Windows portability follow-up — 2026-10-11

The current acceptance and unit checks passed in the combined requested-suite
run; the earlier missing-fact and conflicting-deadline failures recorded above
were not reproduced in this checkout. Text assertions now specify UTF-8, path
checks use POSIX shell form, and the offline guard refuses ordinary loopback
and non-loopback connects while narrowly allowing asyncio's own loopback
`socketpair()` call.
