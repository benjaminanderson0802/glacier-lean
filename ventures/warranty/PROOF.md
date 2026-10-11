# Warranty registration proof

## Card drift check and current status — 2026-10-11

- Checkpoint: PH12.11, Warranty registration.
- Dependencies: PH12 depends on PH5 and PH9. This assigned card is authorized to start; their phase exits are not both recorded in `NORTHSTAR.yaml`, so PH12.11 remains `todo` there.
- Property/metric: P-LOOPS and M-INTERVENE; recurring intake reduces manual deadline tracking while every consequential action stays owner-controlled.
- Existing tool (I-01): use the shared read-only Jobber GraphQL connector and existing Glacier flows; no new integration/tool was built.
- Acceptance first (I-03): `ventures/warranty/tests/acceptance/test_v_warranty2.py`, `ventures/warranty/tests/acceptance/test_C_warranty_rules.py`, and the prewritten `ventures/warranty/tests/test_owner_steps.py`. No acceptance-folder file was edited.

The venture manifest is `ready` for its bounded local intake-preparation scope. The roadmap checkpoint remains `todo` pending its evidence and dependency exit rules. Live account access, recurring production OAuth, marketplace publication, email sending, and portal submission are not represented as complete.

## Fixture-tested

The acceptance run uses the project interpreter:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/warranty -q
```

The 2026-10-10 run reported `23 passed`; the current card's test result is recorded below after verification.

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

Attempted in this worktree. It stopped before network access because `jobber_access_token` is not configured in Glacier's secret store. No credentials were printed and no live account data was read. The exact one-session owner setup is now in [`OWNER-STEPS.md`](OWNER-STEPS.md); it covers the four Job fields and an optional short-lived read test. Jobber GraphiQL access tokens expire after 60 minutes and are testing-only, so this result is not evidence of a recurring live account connection. No live response is claimed.

## Earlier synthetic Glacier dry-run

Existing evidence from the prior implementation records a real Glacier dry-run against a synthetic Carrier record. It reached `waiting` at the deadline review with a three-day alert and no external action: `evidence/ventures/warranty/dry-run-result.json`. It does not prove the new Jobber GraphQL path or live-account behavior. The screenshot remains pending.

The PH12.11 roadmap checkpoint remains `todo` in `NORTHSTAR.yaml`; its status was not changed because this card has not established live Jobber evidence or the PH12 exit. The venture manifest's `ready` status is scoped to its local, read-only preparation workflow and short-lived test mode.

## PH12.11 release-gate work — 2026-10-10

### Official brand registration and serial guidance

Six brand-family records are in [`brands/`](brands/). Each has direct official manufacturer URLs for the portal and warranty sources, a registration deadline where a current official page gives one, who the portal says may register, a separate dealer/third-party terms assessment, and serial date-code guidance when an official source publishes it. Unclear or product-limited cases say `uncertain - please check`. Queue rows carry a compact summary and a `source_record` path to the complete source-backed data; full URL citations are kept in the brand records. Portal automation remains disabled for every family.

The documented windows are 90 days for eligible Carrier/Bryant residential coverage and 60 days for eligible Trane/American Standard, Lennox, Goodman/Amana, and Daikin coverage. Exceptions, product eligibility, and regional rules remain in the cited manufacturer records. Rheem/Ruud's public HVAC material reviewed here does not establish one deadline for all products, so the queue does not calculate a registration deadline for that family. Official date-code guidance is scoped to the product families in each source; serial parsing remains disabled and queue entries remain held for manual checking.

### Jobber mapping and pre-written setup

[`JOBBER-SETUP.md`](JOBBER-SETUP.md) documents the checked query mapping against Jobber's official GraphQL docs: Jobs expose `id`, `jobNumber`, `title`, `jobStatus`, `completedAt`, `jobberWebUri`, and `customFields`; `Client` exposes `name` and `email`; Jobs can return a related `property` and its address. Job custom fields are returned as `CustomFieldUnion`; the connector selects `CustomFieldText { id label valueText }`. It sends API version `2026-04-16` with read-only queries. [`JOBBER-SETUP.md`](JOBBER-SETUP.md) now pre-writes each exact field name, Text type, blank default, non-transferable setting, and example value. Jobber Help Center documents the Gear → Settings → Custom Fields path and warns custom fields are available only on select plans; the owner is told not to upgrade without separate approval.

### Real Glacier engine run on five local fixture jobs

The five synthetic Jobber-shaped completed jobs in [`fixtures/jobber-warranty-jobs-five.json`](fixtures/jobber-warranty-jobs-five.json) ran through the installed `hourly-intake` flow on the real FastAPI/DBOS runtime. For this isolated run only, the disposable installed command was pointed at the checked-in fixture; the committed flow still reads Jobber. Run `584683af2c47` completed with `hourly=done` and `read_jobber=done`. It produced five registration queue rows with family guidance, five held `uncertain — please check` assessments, and five drafts with `sent: false`; every portal automation flag was false. The full engine output is [`evidence/engine-output-2026-10-10.json`](evidence/engine-output-2026-10-10.json), and API/run metadata plus the SHA-256 are in [`evidence/engine-run-2026-10-10.json`](evidence/engine-run-2026-10-10.json). The engine captured 15,735 stdout characters, below its 20,000-character output limit.

No Jobber account, manufacturer portal, homeowner email, or registration endpoint was contacted. The fixture is synthetic evidence of the local flow only. Live Jobber access remains unverified and requires the owner to connect a test account. The first marketplace listing, sending the first drafts, and manufacturer portal automation are outside the ready scope and remain disabled. Terms that do not establish permission for an outside service remain explicitly uncertain; there is no owner terms-review step for this Jobber-only local workflow.

### Manufacturer terms review — 2026-10-11

The official [Daikin terms](https://daikincomfort.com/terms-of-use) expressly prohibit automated systems from monitoring or copying Daikin sites. [Trane website terms](https://www.trane.com/content/dam/Trane/Commercial/global/terms-and-conditions-of-use.pdf) restrict robots or automated processes from monitoring or copying its web pages without express prior written permission. [Carrier terms](https://www.carrier.com/us/en/terms-of-use/) restrict devices/programs/methodologies used to access, acquire, copy, or monitor website content. The reviewed [Goodman legal terms](https://www.goodmanmfg.com/legal) reference Daikin Services terms; these reviewed site terms do not establish permission for an outside service to prepare contractor registrations. For Rheem/Ruud and Lennox, reviewed official sources likewise do not expressly grant that permission. This summary is not a legal interpretation of each registration portal's scope. Brand files preserve `uncertain - please check` where permission is not explicit. Since the current workflow reads Jobber only and does not access manufacturer sites, the uncertainty is a future portal-feature gate rather than a blocker to local intake preparation.

## Current card checks

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/warranty` — **39 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/tests` — **24 passed, 2 subtests passed**.

### Requested test boards

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/warranty -q` — prior recorded result **23 passed**; current result pending.
- `PYTHONPATH=. ~/w/glacier-lean/.venv/bin/python -m pytest ventures/coop-postcards -q` — **16 passed**.
- `PYTHONPATH=. ~/w/glacier-lean/.venv/bin/python -m pytest ventures/blocks -q` — **59 passed, 3 failed** in the existing portal-filer browser tests because `ventures/blocks/filer/runner.mjs` cannot find `glacier/web/node_modules/playwright`. This matches the pre-existing failure already recorded above; no blocks files or checks were changed in this warranty card.

## Other venture test checks

From each venture directory, using `PYTHONPATH` set to the worktree root where the package imports require it: Apify 10 passed/3 subtests; Carpenter Goods 6; Co-op 9; CPSC 18; DIBBS 11; FDA 9; Freight 23; OSHA 8; Property Tax 6; Recall Actor 10 passed/1 skipped/3 subtests; Utility Audits 9. Warranty's current result is recorded above.

The broader checks exposed unrelated existing issues: Recall Checker has 10 passed and 1 failure because its expected no-match wording differs from the implementation (`ventures/recall-checker/tests/test_recall_checker.py::test_clean_item_uses_required_source_and_date_vocabulary`); `ventures/blocks` has 59 passed and 3 portal-filer failures because `ventures/blocks/filer/runner.mjs` cannot load its Playwright module (`MODULE_NOT_FOUND`). Running all `ventures` from the repository root also causes package-root import collection errors; those packages pass when run from their own directories with the worktree root on `PYTHONPATH`. None of these files are in this warranty card.
