# C-SAM-COLLECTOR-TESTER independent findings

## Drift check

- **Checkpoint:** PH12.5 (shared government data feeds and deadline tracker), explicitly authorized in parallel by the card. PH12 is in progress; PH5/PH9 remain in progress, so this does not claim a phase exit.
- **Properties and metrics:** P-VERIFY / M-VERIFIED for independent acceptance; P-LOOPS / M-SURVIVE for repeated bounded capture and fail-closed behavior.
- **Existing tools:** the merged SAM collector, digest snapshot validator and pytest are sufficient. No API client, service or dependency was added.
- **Acceptance written first:** frozen paginated API fixtures preserve full records and capture provenance; only complete snapshots are saved; incomplete pages, duplicate conflicts and source errors remain explicit; missing deadlines remain uncertain; a collector-produced snapshot is directly digestible without rewriting its records; digest history wording remains bounded to the observed snapshots.

## Source review

Read `SOURCE-SETUP.md`, `ACCEPTANCE.md`, `DISPUTE.md`, `ventures/blocks/feeds/IMPORT.md`, and the collector/digest changes in commits `da83692` and `0c305fe`. The requested `ventures/sam-amendment-alerts/PROOF.md` does not exist in this checkout. The corrected F-SAM2 fixture in `tests/test_digest.py` was preserved and not edited.

## Results

The new fixture-based acceptance checks prove that successful two-page capture retains the exact frozen rows, source endpoint, query scope, timestamp/date, and success/count metadata. Partial pagination, page bounds, duplicate rows/conflicts, HTTP 429 and API error envelopes do not write a new complete file or replace an existing file. The digest marks a valid missing-deadline event uncertain and retains the explicit limitation that it does not reconstruct history before the first snapshot.

The direct collector-to-digest acceptance check fails. `collect_snapshot()` emits `total_records`, `query_scope.naics_codes`, and only aggregate `pages_fetched` metadata. `build_digest()` requires `totalRecords`, `limit`, `offset`, and for multi-page captures a contiguous `page_coverage` list. Therefore a collector-produced snapshot is rejected with `Earlier snapshot is missing valid v2 pagination metadata.` The unchanged notice records are present, but the integrated acceptance goal is not met. No confident event or no-match is produced because the digest rejects the input.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests/acceptance/test_C_sam_collection.py` — **1 failed, 9 passed**. Full output: [new-check.log](new-check.log). The failure is the direct collector-to-digest incompatibility above.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/sam-amendment-alerts/tests` — **1 failed, 43 passed, 1 skipped**. Full output: [venture-suite.log](venture-suite.log). The same integration check is the only failure.
- No live API call was made; only frozen offline fixtures were used.

## Disposition

Tester-only scope does not permit editing collector or digest code. The PH12.5 acceptance is not fully verified until collector metadata carries the digest's documented pagination contract (including per-page offsets/counts for multi-page and multi-NAICS captures) or a separately authorized integration change reconciles the formats. Do not mark PH12.5 done based on this evidence alone. No checkpoint status was changed.

Re-read `NORTHSTAR.yaml` anti-patterns: no harness-only check or rewritten existing check was found; this adds an acceptance test against the actual collector/digest handoff. The recorded failure is a product integration gap, not a reason to weaken the acceptance check.
