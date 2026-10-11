# C-FDA-READER-BOUNDARY-TESTER results

## Drift check

- Checkpoints: PH12.15 and shared-reader PH12.4. PH5 and PH9 remain in progress; Northstar records the owner's PH12 authorization.
- Properties and metrics: P-VERIFY, P-CONTROL, M-VERIFIED, M-AUDIT.
- Existing tools: the shared reader and FDA packet preparation are reused; this card adds no parser or implementation.
- Acceptance: agreement preserves field/source-page provenance; disagreement or missing page evidence is uncertain and cannot produce a listing ZIP.

## Independent temporary label examples

The acceptance test creates temporary label text files and injects two independent reader result streams. No existing label fixture, reader contract, implementation, or existing check is changed.

| Case | Field | Reader A | Reader B | Source page | Expected/observed packet result |
|---|---|---|---|---:|---|
| Agreed label | ingredients | Water, Glycerin, Fragrance | Water, Glycerin, Fragrance | 1 | `match`; SPL ZIP produced; all prepared fields have a source |
| Disputed label | ingredients | Water, Glycerin, Fragrance | Water, Fragrance, Glycerin | 1 | `uncertain — please check`; no SPL ZIP; source and page retained |
| Missing page evidence | ingredients | Water, Glycerin, Fragrance | Water, Glycerin, Fragrance | missing | Expected uncertain/no ZIP; observed reader certain and FDA `match` with ZIP |

The FDA report includes source references for every prepared field. Only the label-derived `ingredients` field has a label page number; fields from `brand-details.json` have JSON pointer sources and no label page.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests/acceptance/test_C_reader_boundary.py` — **2 passed, 2 failed**. Agreement and disagreement checks pass. Both missing-page checks fail: the reader reports `uncertain: false`, and FDA returns `match` with a ZIP.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/reader/tests` — **3 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests/test_fda_cosmetics.py ventures/fda-cosmetics/tests/acceptance/test_v_fda2.py` — **17 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics` — **19 passed, 2 failed**, with the same two missing-page failures from the new acceptance test.

The first interpreter path specified in the root AGENTS.md (`/workspaces/glacier-lean/.venv/bin/python`) does not exist in this worker environment. The card's prescribed `~/w/glacier-lean/.venv/bin/python` project interpreter was used instead.

## Boundary finding

Missing source-page evidence is not currently treated as uncertainty by the shared reader, and FDA packet preparation accepts the agreed value and creates an SPL ZIP. This is recorded as a failing independent acceptance test; implementation and the shared reader contract remain untouched in this tester lane.
