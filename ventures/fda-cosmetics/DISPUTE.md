# Historical acceptance fixture dispute

An earlier proof note recorded a JSON parse failure in the protected Shopify acceptance fixture. That report is stale in the current tree: the fixture parses, and `~/w/glacier-lean/.venv/bin/python -m pytest ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py -q --runxfail` currently passes all 3 checks. This card did not modify the protected fixture or acceptance test.

The historical claim `CLM-2026-10-10-PH12-15-LABEL-TEST-FIXTURE` was resolved with the current passing check and linked evidence.
