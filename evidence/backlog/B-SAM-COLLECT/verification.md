# B-SAM-COLLECT verification

## Acceptance

The independent, spec-only evaluator froze [acceptance-contract.md](acceptance-contract.md) before the collector implementation. A clean independent harness then passed all six contract cases; see [evaluator-result.md](evaluator-result.md). The contract covers successful multipage capture, quota and partial-page failures, page/record truncation, missing Glacier Secrets, and credential-free provenance. The builder added ordinary unit fixtures only under the card-authorized `tests/unit/` path; no existing acceptance or CHECK file was changed.

## Commands and results

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests/unit/test_B-SAM-COLLECT_snapshot.py` — **10 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests` — **6 failed, 23 passed, 1 skipped**. All six failures are in the existing read-only `tests/acceptance/test_sam_amendment_alerts.py` digest checks: notice UI link selection, partial-page uncertainty, missing retrieval timestamp, malformed row uncertainty, missing-deadline uncertainty, and conflicting duplicate uncertainty. The same six failures reproduced before collector changes; see [the separate-lane claim](../../../vault/claims/2026-10-11-sam-digest-baseline-acceptance.md). No out-of-scope fix was attempted.
- `git diff --check` and `~/w/glacier-lean/.venv/bin/python -m py_compile ventures/sam-amendment-alerts/scripts/collect_snapshot.py ventures/sam-amendment-alerts/tests/unit/test_B-SAM-COLLECT_snapshot.py` — passed.

## Fixture versus live evidence

Fixture transport proved complete two-page pagination, requested query offsets, retrieval metadata, credential-free source URL, missing-key no-request behavior, secret redaction, quota failure, malformed later page rejection, and page/record-bound failures. Failed fixture runs did not create a snapshot.

A real FastAPI backend was started with a disposable `GLACIER_HOME` and a temporary command flow. The collector command failed as expected because that home had no SAM secret; Glacier surfaced the “Settings → Secrets” and retry guidance, and no snapshot was written. A read-only check of the current Glacier secret-name index found no configured `sam_api_key`, so no external SAM.gov request was made. **Live SAM pagination and source records remain unverified.**

## Limits

This card adds a command-line collector and setup note only. It does not change the pilot flow or schedule; V-AUTOMATE owns that work. The owner must configure `sam_api_key` in Glacier Settings → Secrets, verify current SAM.gov API terms/rate limits, then collect two bounded live snapshots before treating the pilot as source-verified.
