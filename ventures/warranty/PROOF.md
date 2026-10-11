# Warranty registration proof

## Fixture-tested

The acceptance run uses the project interpreter:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/warranty -q
```

Result after this card's changes: `23 passed`.

The connector and end-to-end fixture checks:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py ventures/warranty/tests/test_warranty.py
```

The earlier implementation run reported `38 passed`; after this card's additional tests, the combined count is superseded by the three suite results at the end of this file. The Jobber fixture is synthetic and API-shaped: `data.jobs.nodes`, cursor `pageInfo`, `extensions.cost`, API version metadata, encoded IDs, Jobber text custom fields, completion data, client email/name, and property region. The tests assert the read query requests the fields and version, maps that response into a deadline queue, emits a homeowner draft, leaves it unsent, and persists the local queue for the daily flow. A separate check confirms Jobber's completion timestamp is not misused as the installation date. No live Jobber response is represented by this fixture.

The Jobber client remains query-only for GraphQL reads. The warranty command saves its local pending deadline input under `GLACIER_HOME/ventures/warranty/pending-units.json`, then outputs the queue and draft. Serial validation remains disabled; the fixture record returns `uncertain — please check` while still calculating its Carrier deadline. Portal automation is disabled and no email is sent.

## Live connection check

One-command owner check:

```sh
~/w/glacier-lean/.venv/bin/python ventures/warranty/scripts/owner_check.py
```

Attempted in this worktree. It stopped before network access because `jobber_access_token` is not configured in Glacier's secret store. No credentials were printed and no live account data was read. After the owner saves all four Jobber OAuth values in Glacier Settings → Secrets, rerun the command to produce live output. Five eligible account checks, owner review, publishing, and sending remain owner actions.

## Earlier synthetic Glacier dry-run

Existing evidence from the prior implementation records a real Glacier dry-run against a synthetic Carrier record. It reached `waiting` at the deadline review with a three-day alert and no external action: `evidence/ventures/warranty/dry-run-result.json`. It does not prove the new Jobber GraphQL path or live-account behavior. The screenshot remains pending.

The venture checkpoint remains unverified. No status in `NORTHSTAR.yaml` was changed.

## PH12.11 release-gate work — 2026-10-10

### Official brand registration and serial guidance

Six brand-family records are in [`brands/`](brands/). Each has direct official manufacturer URLs for the portal and warranty sources, a registration deadline where a current official page gives one, who the portal says may register, a separate dealer/third-party terms assessment, and serial date-code guidance when an official source publishes it. Unclear or product-limited cases say `uncertain - please check`. Queue rows carry a compact summary and a `source_record` path to the complete source-backed data; full URL citations are kept in the brand records. Portal automation remains disabled for every family.

The documented windows are 90 days for eligible Carrier/Bryant residential coverage and 60 days for eligible Trane/American Standard, Lennox, Goodman/Amana, and Daikin coverage. Exceptions, product eligibility, and regional rules remain in the cited manufacturer records. Rheem/Ruud's public HVAC material reviewed here does not establish one deadline for all products, so the queue does not calculate a registration deadline for that family. Official date-code guidance is scoped to the product families in each source; serial parsing remains disabled and queue entries remain held for manual checking.

### Jobber mapping verification

[`JOBBER-SETUP.md`](JOBBER-SETUP.md) documents the checked query mapping against Jobber's official GraphQL docs: Jobs expose `id`, `jobNumber`, `title`, `jobStatus`, `completedAt`, `jobberWebUri`, and `customFields`; `Client` exposes `name` and `email`; Jobs can return a related `property` and its address. Job custom fields are returned as `CustomFieldUnion`; the connector selects `CustomFieldText { id label valueText }`. It sends API version `2026-04-16` with read-only queries. Jobber's official docs say custom fields support a Text type and can be configured manually by an account admin. The exact four Job fields the shop creates are Equipment Brand, Equipment Model, Equipment Serial, and Install Date, all Text. The official changelog has a `2026-04-16` entry; it lists enum additions unrelated to this query.

### Real Glacier engine run on five local fixture jobs

The five synthetic Jobber-shaped completed jobs in [`fixtures/jobber-warranty-jobs-five.json`](fixtures/jobber-warranty-jobs-five.json) ran through the installed `hourly-intake` flow on the real FastAPI/DBOS runtime. For this isolated run only, the disposable installed command was pointed at the checked-in fixture; the committed flow still reads Jobber. Run `584683af2c47` completed with `hourly=done` and `read_jobber=done`. It produced five registration queue rows with family guidance, five held `uncertain — please check` assessments, and five drafts with `sent: false`; every portal automation flag was false. The full engine output is [`evidence/engine-output-2026-10-10.json`](evidence/engine-output-2026-10-10.json), and API/run metadata plus the SHA-256 are in [`evidence/engine-run-2026-10-10.json`](evidence/engine-run-2026-10-10.json). The engine captured 15,735 stdout characters, below its 20,000-character output limit.

No Jobber account, manufacturer portal, homeowner email, or registration endpoint was contacted. The fixture is synthetic evidence of the local flow only. The owner's live Jobber test account still needs five eligible records and owner review of the listing and the first 20 drafts. Any portal terms not clearly authorizing an outside service remain marked uncertain and require the owner to check them before deciding on future automation.

### Requested test boards

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/warranty -q` — **23 passed**.
- `PYTHONPATH=. ~/w/glacier-lean/.venv/bin/python -m pytest ventures/coop-postcards -q` — **16 passed**.
- `PYTHONPATH=. ~/w/glacier-lean/.venv/bin/python -m pytest ventures/blocks -q` — **59 passed, 3 failed** in the existing portal-filer browser tests because `ventures/blocks/filer/runner.mjs` cannot find `glacier/web/node_modules/playwright`. This matches the pre-existing failure already recorded above; no blocks files or checks were changed in this warranty card.

## Other venture test checks

From each venture directory, using `PYTHONPATH` set to the worktree root where the package imports require it: Apify 10 passed/3 subtests; Carpenter Goods 6; Co-op 9; CPSC 18; DIBBS 11; FDA 9; Freight 23; OSHA 8; Property Tax 6; Recall Actor 10 passed/1 skipped/3 subtests; Utility Audits 9. Warranty's 19-pass run is above.

The broader checks exposed unrelated existing issues: Recall Checker has 10 passed and 1 failure because its expected no-match wording differs from the implementation (`ventures/recall-checker/tests/test_recall_checker.py::test_clean_item_uses_required_source_and_date_vocabulary`); `ventures/blocks` has 59 passed and 3 portal-filer failures because `ventures/blocks/filer/runner.mjs` cannot load its Playwright module (`MODULE_NOT_FOUND`). Running all `ventures` from the repository root also causes package-root import collection errors; those packages pass when run from their own directories with the worktree root on `PYTHONPATH`. None of these files are in this warranty card.
