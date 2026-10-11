# C-JOBBER-CONNECTOR-TESTER acceptance

## Drift check

- Checkpoint: PH12.8, platform connectors. PH5 and PH9 remain in progress; PH12 work is explicitly parallel-authorized.
- Defining properties and metrics: P-CONTROL / M-AUDIT for read-only, bounded scope; P-VERIFY / M-VERIFIED for independent fixture-backed mapping checks.
- Existing tools: the Jobber connector and venture mappers already exist; add no integrations, dependencies, credentials, or API scopes.
- Acceptance command: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_C-JOBBER-CONNECTOR-independent.py` and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests`.

## Acceptance test, written before edits

Using synthetic, customer-authorized-shape Jobber fixtures and mocked HTTP transport only:

1. A completed job maps to closeout and warranty inputs with the original job, client, property, and custom-field IDs; completion status/date; and Jobber read-only provenance intact.
2. The only network requests are POST GraphQL queries to Jobber's documented GraphQL endpoint, with the pinned API version and only the connection-check or job fields required by the mapping. Mutation attempts fail before transport.
3. Missing permissions, GraphQL partial data, pagination beyond the configured limit, and absent optional fields fail closed or remain explicitly uncertain.
4. Tests do not use credentials, a live account, customer data, writes, sends, or external API calls.

Evidence is the captured output of both pytest commands; this is fixture evidence only and makes no connected-account claim.
