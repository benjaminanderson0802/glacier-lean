# Release check: platform connectors

## Drift check

1. Checkpoint: PH10.4, community connectors with review and provenance. This card advances its platform connector portion. PH8 and PH9 are still in progress; assigned work may start, but PH10.4 cannot be re-marked complete here.
2. Dependencies: PH8 and PH9 have not reached their exits. This is an assigned card; no checkpoint status is changed.
3. Defining properties and metrics: P-CONTROL / M-AUDIT (read-only calls prevent unapproved writes and are bounded); P-SECURE / M-SECURITY (secrets stay in the OS keychain and errors omit credentials); P-USABLE / M-TTFA (one-command account checks).
4. Existing tool: Glacier's `secrets_store` and pinned `httpx` already cover keychain storage and HTTP transport. This block adds platform-specific query shapes, OAuth refresh for Jobber, pagination, bounded retries, and connector-specific check commands; no new dependency is introduced.
5. Acceptance test: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py`. Tests use static fixtures derived from official API documentation and mock transports; they cover pagination, retries, read-only behavior, safe credential use, and connection checks. Live account checks are owner steps listed below.

## Release checks

1. Fixture-backed tests pass with the command above.
2. After saving the named key(s) in Glacier Secrets, the owner runs one command per platform from the repository root:
   - `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors jobber`
   - `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors shipstation`
   - `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors shopify --shop STORE.myshopify.com`
   - `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors apify`
3. Each command must return `connected: true` without displaying credentials. Real-account checks remain pending until the owner configures test accounts and secrets.

## Fixture provenance

`fixtures/SOURCES.md` lists official API documentation for the response shapes. Fixture values are synthetic and contain no account or customer data. The tests never call production APIs.
