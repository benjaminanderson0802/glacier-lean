# B-FEED-QUARANTINE independent acceptance result

- **Source revision evaluated:** `f1dbc7ef110ae7b031972ff0615a280c38b2670f`
- **Result:** Pass for the observable synthetic acceptance contract below.
- **Scope:** Independent synthetic fixture-through-adapter evidence. This is not a live-source check or a PH12.5 phase-exit claim.

## Run method and fixture

Used `.venv/bin/python` (the documented `/workspaces/glacier-lean/.venv/bin/python` path was absent in this checkout) to run an inline Python harness. The harness imported `ventures.blocks.feeds.core`, supplied a temporary synthetic registry and fixture `fetch_source`, and exercised the adapter's `sync(SOURCE)` and `query(SOURCE)` methods. Each case used a fresh `GLACIER_HOME` and disposable SQLite database under `/tmp`; no government or other live source was contacted.

R1 contained two uniquely identified complete records with fields `canary`, `id`, `name`, and `required`; S1 was the sorted set of those four fields. The configured canary field was `canary`. Before each suspect refresh, the harness imported R1, queried it, and reopened the storage through subsequent independent queries. Rows were compared as complete records, ignoring order.

The adapter has no public schema-query method. To verify remembered schema and its persistence across reopened connections, the harness read `feed_schemas.fields` from the disposable local SQLite database. This schema check is therefore a local storage inspection, not a public query/API observation.

## Results

| Case | Refresh result | Rows/schema after reopen | Outcome |
|---|---|---|---|
| Source count mismatch: 98 candidate rows, source total 100 | `failed`, `snapshot_available: true`, `changed: false`; row-count alert identified the difference as greater than 1% and result said the previous trusted snapshot was retained | Exactly R1 and S1 | Pass |
| Missing canary: complete count and unchanged field set, with `canary: null` on each row | `failed`, `snapshot_available: true`, `changed: false`; canary alert and quarantine/retention disposition | Exactly R1 and S1 | Pass |
| Required schema field removed: complete count and canary retained, `required` omitted | `failed`, `snapshot_available: true`, `changed: false`; schema-change alert and quarantine/retention disposition | Exactly R1 and S1 | Pass |
| Valid replacement R2: different complete rows, matching count, canary and S1 fields | `ok`, `changed: true` | Exactly R2 and S1 | Pass |
| First import failure: empty store, invalid candidate missing a usable canary | `failed_initial`, `snapshot_available: false`; result explicitly stated no trusted snapshot was available | No trusted rows and no remembered schema | Pass; distinguishable from a rejection retaining R1/S1 |

For the missing-canary fixture, the canary key remained present with a null value. That kept the candidate schema unchanged and isolated the canary rejection.

## Atomicity and failure injection

During the valid R1-to-R2 replacement, a temporary SQLite trigger paused inside the schema UPSERT, after the row changes had run inside the writer transaction. Independent calls to the public `query()` surface ran concurrently. Across 72 observations, the only observed states were R1/S1 and R2/S1; both were observed, and no partial or mixed state appeared. The final reopened state was R2/S1.

For promotion failure, a separate temporary SQLite `BEFORE UPDATE` trigger raised an injected abort during the schema UPSERT in the same row/schema promotion transaction. The refresh returned `failed`, `snapshot_available: true`, `changed: false`. Reopening storage returned exactly R1 and S1, demonstrating rollback of the candidate row replacement.

## Evidence limits

All candidate and baseline data were synthetic and passed through the local adapter with its fetch function replaced by the fixture provider. The run did not validate a real source, production data, network behavior, or a phase exit. Schema persistence was checked directly in disposable SQLite because schema is not exposed through the adapter's public query surface. The working tree also showed untracked `.venv` and `glacier/web/node_modules`; this run did not modify them, and their prior state was not established.
