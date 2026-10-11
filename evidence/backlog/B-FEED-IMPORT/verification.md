# B-FEED-IMPORT verification

## Drift check and acceptance

- **Checkpoint:** PH12.5, shared government data feeds and deadline tracker.
- **Dependencies:** PH12 depends on PH5 and PH9, both still `in_progress`. Feed work was serialized after B-FEED-QUARANTINE; this change makes no phase-exit or checkpoint-completion claim.
- **Properties and metrics:** P-LOOPS and P-VERIFY; M-VERIFIED and M-INTERVENE.
- **Existing-tool choice:** Reused the feed registry, existing JSON/CSV/HTML/XLSX/ZIP readers, SQLite snapshot cache, and the existing canary/count/schema checks. No package, paid service, network workaround, or new store was added.
- **Acceptance written before implementation:** Import saved source bytes offline with URL/date/hash/format/count/completeness provenance; quarantine malformed, stale, HTML error/consent, incomplete, count-mismatched, canary-missing, and schema-changed candidates while retaining trusted rows/schema; accept JSON/CSV/HTML through current schemas; repeat identical bytes without changing the snapshot; report no live fetch.

## Reproduction

Before implementation, the card-specific test could not collect because `ventures.blocks.feeds.import_snapshot` did not exist (`ModuleNotFoundError`). This reproduced the missing offline-import capability before product changes.

## Verification

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests
```

Result: **26 passed**. The new unit tests use only synthetic local files and disposable SQLite databases. They cover provenance, byte hash, acquisition-date `fetched_at`, idempotence, stale/incomplete/malformed/error HTML, source-count mismatch, canary and schema quarantine, OSHA CSV, DIBBS HTML, consent-page refusal, FDA ZIP partitions, and clearing import provenance after a successful network refresh. Existing feed tests also pass.

Additional command:

```sh
~/w/glacier-lean/.venv/bin/python -m py_compile ventures/blocks/feeds/core.py ventures/blocks/feeds/import_snapshot.py
git diff --check
```

Both passed.

## Real backend evidence

Started the real FastAPI backend with the project interpreter on `127.0.0.1:18765` and a disposable `GLACIER_HOME=/tmp/glacier-b-feed-import-live`. `/api/health` returned HTTP 200. While that process was live, imported a synthetic one-row FSIS-shaped JSON file against the same disposable home, queried it from the feed cache, and checked persisted provenance. The harness replaced `fetch_source` with an assertion failure; no source request was possible. The first import succeeded with `live_fetch: false`; the repeated import returned `changed: false`, `idempotent: true`; the query's `fetched_at` is the acquisition date. Detailed output is in [real-backend-fixture.json](real-backend-fixture.json).

Evidence classification: **synthetic fixture through real local backend process and local SQLite feed cache**. No official file was available for this run, and no public source was contacted. This is not live-source or owner-data evidence.

## Anti-pattern review and remaining work

The importer is bounded and local-only; it adds no synchronization loop, status file, or duplicate parser dependency. Snapshot rows, remembered schema, and import metadata are promoted in one SQLite transaction. No NORTHSTAR status or evidence fields were changed. Existing owner-download steps remain: Benjamin must supply the official saved file and its acquisition date/completeness confirmation when using this fallback. A separately assigned independent evaluator should run the saved-file acceptance against this revision; ordinary unit tests here are supplemental and do not claim that independent evaluation.
