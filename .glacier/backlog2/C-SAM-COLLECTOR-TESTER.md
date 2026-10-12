# C-SAM-COLLECTOR-TESTER — Independently verify bounded SAM snapshot collection

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `sam-collector-evaluator`. Allowed edits: new `ventures/sam-amendment-alerts/tests/acceptance/test_C_sam_collection.py` and `evidence/backlog2/C-SAM-COLLECTOR-TESTER/`. Collector, digest product code, F-SAM2's `tests/test_digest.py`, existing checks and sales material are read-only.

## Goal

Independently verify the merged collector stores exact, bounded Opportunities API snapshots with complete pagination metadata, source URL, retrieval time and query scope, then hands those unchanged records to the digest. Partial pages, duplicate conflicts, missing deadlines and API errors must remain explicit uncertainty; never imply a full amendment history beyond the supported API.

Read first: `ventures/sam-amendment-alerts/SOURCE-SETUP.md`, `ACCEPTANCE.md`, `PROOF.md`, `DISPUTE.md`, `ventures/blocks/feeds/IMPORT.md`, commits `da83692` and `0c305fe`.

## Drift check

- Checkpoint: PH12.5. PH5/PH9 remain in progress; PH12 feed work is explicitly owner-authorized in parallel.
- Properties/metrics: P-VERIFY, P-LOOPS; M-VERIFIED, M-SURVIVE.
- Existing tools: merged SAM collector, current snapshot validator and pytest; no new API client or service.
- Acceptance first: frozen paginated fixtures retain complete metadata and unchanged rows; incomplete/overlapping/conflicting snapshots cannot produce confident events or no-match results.

## Verification

Run the new check and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests`. A live API call is optional and only if an already-configured authorized key is available; never print or commit credentials. Preserve the current F-SAM2 fixture correction and all acceptance checks.
