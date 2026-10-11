# B-FEED-QUARANTINE verification

## Drift check

- Checkpoint: PH12.5, shared government data feeds and deadline tracker.
- Dependencies: NORTHSTAR records PH12 depends on PH5 and PH9; PH5 is still in progress. The launch card authorizes scoped work, but this task makes no phase-exit or checkpoint-completion claim.
- Properties and metrics: P-VERIFY and P-LOOPS; M-FALSE-DONE and M-SURVIVE.
- Existing tool: the current standard-library adapter and SQLite snapshot store are reused; no scheduler, database, service, or dependency was added.
- Acceptance first: see [acceptance-contract.md](acceptance-contract.md), frozen by an independent spec-only evaluator before the implementation was complete.

## Reproduction

Before the fix, a disposable `GLACIER_HOME` and `cpsc_recalls` adapter fixture first stored one trusted row. Three subsequent candidates were tried independently: 1 row against a source total of 100, a row without `RecallNumber`, and a row with `RecallTitle` removed. Each result returned `changed: true`; each query returned the candidate instead of the trusted row. The remembered schema also changed on the latter two candidates. This reproduced all three quarantine failures without contacting a public source.

## Verification

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests
```

Result: **21 passed**. Captured in [feed-tests.log](feed-tests.log).

The new card-specific unit tests exercise the normal feed interface and the production SQLite cache with synthetic data. They cover all three rejected candidates, retained rows and schema, a successful complete replacement, rollback when schema persistence fails during promotion, and the failed-first-import distinction. Existing stream and database tests also pass.

Additional checks passed:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m py_compile ventures/blocks/feeds/core.py
git diff --check
```

Evidence classification: **fixture-through-real-local-SQLite evidence**. No live government source request or real-source count was made for this code change. The existing live-source results in `ventures/blocks/feeds/CHECK.md` predate this change and are not represented as its proof.

## Implementation notes

Suspect candidates now return a failed status and a clear retained-snapshot or first-import message. Normalization compares schemas without remembering candidates. Accepted snapshots write rows and remembered schema in one SQLite transaction. The Socrata full and incremental paths also stage rows and validate before promotion.

Anti-pattern review: no new custom governance layer or status claim was added. The verification artifact and tests describe fixture behavior only; NORTHSTAR status and checkpoint evidence were not changed.
