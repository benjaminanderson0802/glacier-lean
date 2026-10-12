# C-JOBBER-CONNECTOR-TESTER — Independently verify read-only Jobber mapping

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `jobber-connector-evaluator`. Allowed edits: new tests under `ventures/blocks/connectors/tests/` named with `C-JOBBER-CONNECTOR` and `evidence/backlog2/C-JOBBER-CONNECTOR-TESTER/`. Connector implementation and existing checks are read-only.

## Goal

Check that a customer-authorized Jobber-shaped fixture maps completed job fields to downstream packet inputs without losing IDs, completion state or provenance, and never issues a write or fetches outside approved read scopes. This supports closeout and venture readiness; it is not a connected customer test.

Read first: `ventures/blocks/connectors/README.md`, `CHECK.md`, `ventures/job-closeout/ACCEPTANCE.md`, `ventures/warranty/ACCEPTANCE.md`.

## Drift check

- Checkpoint: PH12.8. PH5/PH9 remain in progress; PH12 is parallel-authorized.
- Properties/metrics: P-CONTROL, P-VERIFY; M-AUDIT, M-VERIFIED.
- Existing tools: existing connector adapter and fixtures; no added integration or API scope.
- Acceptance first: valid read-only response maps exactly; absent permissions, partial pages, null fields and unexpected writes fail closed with explicit uncertainty.

## Verification

Run the new check and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests`. No owner credentials, live account, writes, sends or customer records.
