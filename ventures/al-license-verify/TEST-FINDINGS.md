# Independent acceptance findings — al-license-verify

The acceptance checks are independent of the roster matcher and Actor wrapper.
Run date: 2026-10-10.
Source fields and the board's dated-data limitation are documented in
[ACCEPTANCE.md](ACCEPTANCE.md). The one live canary opened the official Alabama
General Contractors Licensing Board site (HTTP 200; `License Roster` marker).
It did not scrape a roster or call an Actor. Output is captured in
[`tests/acceptance/evidence/live-canary.log`](tests/acceptance/evidence/live-canary.log).

Offline run: `~/w/glacier-lean/.venv/bin/python -m pytest -q -k 'not live_official_document_contract' tests/acceptance` — **5 failed, 20 passed, 1 deselected**. Failures are left in place:

- The legacy unit test initially expected the lookup date instead of the supplied
  roster's `roster_as_of` date. The implementation and independent acceptance
  check use the snapshot date; the stale unit expectation is corrected in
  `tests/test_alabama_roster.py` (see [DISPUTE.md](DISPUTE.md)).
- Different non-Latin names normalize to the same empty comparison key and
  falsely return a match.
- An invalid expiration string is emitted in a verified match.
- Mocked 429 and 503 source outages abort without an uncertain customer result.
  The mock Actor records no output and no charge in either outage case.

Prospect review: the listed contacts are municipal offices from the Alabama
League of Municipalities public organization roster, not private individuals;
the routes ask for purchasing/public works, and no personal email is present.
The directory supports organization identity/contact provenance but does not
show that each town buys this service or has a licensing-review workflow.
Commercial permission for the roster export remains an owner prerequisite. The
Actor charging test is mocked and permits one charge only after a completed
lookup; no real Actor, paid event, live roster or external action ran.

## Windows portability follow-up — 2026-10-11

The current acceptance and unit checks passed in the combined requested-suite
run. The earlier Unicode-name, expiration, outage, and no-match failures were
not reproduced in this checkout; the no-match discrepancy was a stale legacy
unit expectation and is resolved in [DISPUTE.md](DISPUTE.md). Text assertions
now specify UTF-8, path checks use POSIX shell form, and the offline guard
refuses ordinary loopback and non-loopback connects while narrowly allowing
asyncio's own loopback `socketpair()` call.
