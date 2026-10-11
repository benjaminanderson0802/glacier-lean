# Warranty registration proof

## Fixture-tested

The acceptance run uses the project interpreter:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/warranty -q
```

Result after this card's changes: `20 passed`.

The connector and end-to-end fixture checks:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py ventures/warranty/tests/test_warranty.py
```

Result: `38 passed`. The new Jobber fixture is synthetic and API-shaped: `data.jobs.nodes`, cursor `pageInfo`, `extensions.cost`, API version metadata, encoded IDs, Jobber text custom fields, completion data, client email/name, and property region. The tests assert the read query requests the fields and version, maps that response into a deadline queue, emits a homeowner draft, leaves it unsent, and persists the local queue for the daily flow. A separate check confirms Jobber's completion timestamp is not misused as the installation date. No live Jobber response is represented by this fixture.

The Jobber client remains query-only for GraphQL reads. The warranty command saves its local pending deadline input under `GLACIER_HOME/ventures/warranty/pending-units.json`, then outputs the queue and draft. Brand serial patterns remain unverified; the fixture record returns `uncertain — please check` while still calculating its Carrier deadline. Portal automation is disabled and no email is sent.

## Live connection check

One-command owner check:

```sh
~/w/glacier-lean/.venv/bin/python ventures/warranty/scripts/owner_check.py
```

Attempted in this worktree. It stopped before network access because `jobber_access_token` is not configured in Glacier's secret store. No credentials were printed and no live account data was read. After the owner saves all four Jobber OAuth values in Glacier Settings → Secrets, rerun the command to produce live output. Five eligible account checks, owner review, publishing, and sending remain owner actions.

## Earlier synthetic Glacier dry-run

Existing evidence from the prior implementation records a real Glacier dry-run against a synthetic Carrier record. It reached `waiting` at the deadline review with a three-day alert and no external action: `evidence/ventures/warranty/dry-run-result.json`. It does not prove the new Jobber GraphQL path or live-account behavior. The screenshot remains pending.

The venture checkpoint remains unverified. No status in `NORTHSTAR.yaml` was changed.

## Other venture test checks

From each venture directory, using `PYTHONPATH` set to the worktree root where the package imports require it: Apify 10 passed/3 subtests; Carpenter Goods 6; Co-op 9; CPSC 18; DIBBS 11; FDA 9; Freight 23; OSHA 8; Property Tax 6; Recall Actor 10 passed/1 skipped/3 subtests; Utility Audits 9. Warranty's 19-pass run is above.

The broader checks exposed unrelated existing issues: Recall Checker has 10 passed and 1 failure because its expected no-match wording differs from the implementation (`ventures/recall-checker/tests/test_recall_checker.py::test_clean_item_uses_required_source_and_date_vocabulary`); `ventures/blocks` has 59 passed and 3 portal-filer failures because `ventures/blocks/filer/runner.mjs` cannot load its Playwright module (`MODULE_NOT_FOUND`). Running all `ventures` from the repository root also causes package-root import collection errors; those packages pass when run from their own directories with the worktree root on `PYTHONPATH`. None of these files are in this warranty card.
