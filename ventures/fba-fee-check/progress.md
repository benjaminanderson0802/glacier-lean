# Progress

## 2026-10-10 — PH12 FBA fee pilot kit

Built the CSV-only prototype, fixtures shaped like Amazon Settlement Report V2, acceptance tests, sample digest, schema-valid venture manifest, one-step manual pitch flow, paid-pilot email, and 15 sourced business leads. The prototype does not use SP-API or touch Amazon accounts. The sample is synthetic because Settlement Report V2 rows are seller-specific and no keyless official transaction dataset was available.

Verification: `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fba-fee-check -q` passed (5 tests); `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` passed (18 passed, 1 xfailed, 2 xpassed); `venture.json` validated against `ventures/venture.schema.json`.

No prospect was contacted, no report was received, and no buyer or paid-pilot outcome has been verified. Keep this venture `in_progress` until the owner runs the outreach test and has evidence from a real seller.
