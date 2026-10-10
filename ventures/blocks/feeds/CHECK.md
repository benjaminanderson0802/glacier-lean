# Government data feed release check

Release only when the following pass:

1. `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/feeds/tests` passes, including schema-change, database, canary, and daily-flow checks.
2. `~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync-all` runs against the ten public source endpoints. Record per-source normalized row counts, published totals where available, canary status, and every source/format alert in `evidence/ventures/feeds-live.json`.
3. Where a source publishes a comparable total, normalized row count is within 1% or an alert blocks release. A source that cannot be fetched or whose format has changed is not marked passing.
4. A second run with no source changes reports `changed: false` for unchanged snapshots.
5. `flows/daily_sync.json` has a daily 02:00 schedule and syncs every source in `sources.json`. Alerts route through a durable approval and note step.

Current source set: CPSC HTS flagging list, CPSC citation/testing exception codes, CPSC bulk upload template, CPSC Recalls API, NHTSA flat-file download, FDA openFDA food enforcement, FSIS Recall API, OSHA ITA establishment summary CSV, DLA DIBBS public solicitation page, and Cook County Assessor open data. No authentication, purchase, account creation, bidding, or government submission occurs.
