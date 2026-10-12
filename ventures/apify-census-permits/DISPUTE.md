# Acceptance disputes

## 2026-10-11 F-GEORGIA: Alabama is a Census data market

`tests/acceptance/test_apify_census_permits.py` asserts Alabama as the label for
FIPS 01 in Census data fixtures and output. This is an intentional market/data
expectation, not an owner business-registration instruction, and remains
unchanged.

## 2026-10-11 Windows acceptance run: asyncio socketpair failure

The owner reports Windows-only acceptance failures in asyncio's `socketpair` setup. This is an acceptance-runtime/platform failure, not evidence that the Census HTTP client opened an unapproved connection. Product source collection is synchronous; the Actor wrapper uses the Apify async runtime and delegates source collection with `asyncio.to_thread`. On Windows, event-loop setup can create local socket pairs for its wakeup mechanism. The acceptance network guard must stay intact; do not loosen its socket/connect checks to make this pass.

No Windows traceback was included with this report, and the Linux worker cannot reproduce the platform failure. Keep this as an environment dispute until the independent acceptance runner supplies a Windows traceback and reruns it on its supported Windows setup. The product contract, request allowlist, and network guards are unchanged by this dispute.
