# C-FEED-IMPORT-TESTER — independent snapshot provenance verification

## Drift check and acceptance

- **Checkpoint:** PH12.5, government data feeds and deadline tracker.
- **Dependencies:** PH12 depends on PH5 and PH9, which remain in progress. The task is authorized to run in parallel; this evidence does not mark the checkpoint done.
- **Properties and metrics:** P-VERIFY and P-MEMORY; M-VERIFIED and M-SURVIVE.
- **Existing tools:** exercised the merged `import_snapshot` API, SHA-256, SQLite, and pytest. No new feed system or dependency was added.
- **Acceptance written before checks:** a fully validated dated local source file must preserve its registered source URL, acquisition/retrieval date, source record vintage, exact-byte hash, format, and row count. A repeated identical file must be idempotent. Duplicate-ID, malformed, count-mismatched, and wrong-source candidates must remain untrusted and leave trusted rows, remembered schema, and provenance unchanged.

All imported files in these checks were generated as synthetic local fixtures. The tests prohibit network fetches in the positive provenance path; no public source was contacted and no owner data was used.

## Results

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests/unit/test_C-FEED-IMPORT-independent.py
```

Result: **4 passed, 1 failed**. The passing checks verify byte hash, source URL, acquisition date as `fetched_at`, source record date as its vintage, parsed row count, idempotent repeated import with unchanged provenance, and retention of a trusted snapshot after malformed JSON, a published row-count mismatch, or an unregistered source host.

The failed check supplies two identical rows with the same synthetic source identifier after first importing a separate trusted synthetic row. The importer returns success and promotes the duplicate candidate; the trusted row is replaced. SQLite's `INSERT OR REPLACE` collapses the duplicate identifier instead of rejecting the candidate, so the claimed source total of two also does not correspond to two stored rows. This violates the requested trust and no-overwrite behavior.

Full required suite:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests
```

Result: **34 passed, 1 failed**, with the same duplicate-ID failure. Captured output is in [pytest.log](pytest.log), and final independent output is in [independent-pytest-final.log](independent-pytest-final.log). The focused duplicate reproduction is in [duplicate-case.log](duplicate-case.log).

## Disposition

No importer, registry, or existing check was edited because this card is tester-only. The duplicate-ID acceptance gap needs a fix in the importer lane before these independent checks pass. No checkpoint status or evidence field in `NORTHSTAR.yaml` was changed.

## Anti-pattern review

The new tests exercise the public import path and persisted SQLite state; they do not only test the test harness. Evidence reports the failing behavior and does not claim a passing checkpoint.
