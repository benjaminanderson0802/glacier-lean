# Historical acceptance fixture dispute

An earlier proof note recorded a JSON parse failure in the protected Shopify acceptance fixture. That report is stale in the current tree: the fixture parses, and `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py -q --runxfail` currently passes all 3 checks. This card did not modify the protected fixture or acceptance test.

The historical claim `CLM-2026-10-10-PH12-15-LABEL-TEST-FIXTURE` was resolved with the current passing check and linked evidence.

## Shared reader-contract status — owner reconciliation still needed

The current shared reader acceptance check passes 3/3, and the public FDA reader sample benchmark matched 7/7 known-value fields (see [PROOF.md](PROOF.md)). However, `CLM-2026-10-10-PH12-15-READER-CONFLICT-CONTRACT` is still filed and assigned to B1. This venture card does not edit or close another worker's claim. The measurable disagreement is between the current passing contract/benchmark evidence and the still-open claim; B1 must record whether the fix satisfies the contract and link its independent evidence before PH12.15 can clear this gate.
