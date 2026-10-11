# CPSC data prep proof

## Drift check and acceptance

- Checkpoint: PH12.9. PH12 depends on PH5 and PH9; their phase exits are
  recorded as reached, and wave 6 assigns this venture in parallel.
- Properties/metrics: P-CONTROL and P-USABLE; M-VERIFIED and M-INTERVENE.
- Existing tools / I-01: CPSC provides the Product Registry, API, bulk-upload
  template, and official code guidance. Those cover registry management and
  filing formats, not this venture's local document extraction, source-linked
  review, gap reporting, and customer approval flow. This venture is glue
  around CPSC's system and never certifies or submits data. Sources: [CPSC
  Product Registry](https://www.cpsc.gov/eFiling-CPSC-Product-Registry),
  [eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library).
- Acceptance: tests verify exact-template output, cited source pages, blank
  field gaps, blocking required fields, independent agreement, known tariff and
  rule codes, and customer certification. The venture must never submit to
  CPSC. Live feed checks must return current official source records without
  canary alerts; live feed access alone does not establish batch readiness.

## Venture tests and fixture scope

Command, using the project interpreter:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/cpsc-prep -q
```

Result: `19 passed, 1 skipped, 1 xpassed in 16.12s` on the final run.
The independent lawyer-question/launch-gate acceptance check also passed with
its xfail marker ignored:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest \
  ventures/cpsc-prep/tests/acceptance/test_v_cpsc2.py::test_lawyer_questions_are_cited_and_launch_remains_gated \
  -q --runxfail
```

Result: `1 passed in 0.53s`. The `xpassed` in the full suite is this check
passing under the suite's normal xfail handling.

Installer validation:

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only cpsc-prep --dry-run
```

Result: all four flows (`cpsc-batch-prep`, `cpsc-broker-launch`,
`cpsc-feed-refresh`, and `cpsc-code-pages`) validated successfully.

The pipeline tests use fake reader/feed outputs and a fake independent second
engine; ruleset mapping is checked with the real CPSC rules checker. This is
fixture-tested behavior. It is not evidence of a customer batch processed from
real documents, an independent live model cross-check, or a CPSC filing.

## Live CPSC feed canaries

On 2026-10-10, I ran each CPSC source sync with an isolated `GLACIER_HOME` under
`/tmp/glacier-cpsc-live-canary-20261010`. The source adapter uses a descriptive
Glacier public-data User-Agent and sends a read-only GET; it did not log in,
create an account, use an API key, or submit data. The CPSC records came from
the official [eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library)
and the [SaferProducts.gov CPSC Recalls REST service](https://www.saferproducts.gov/RestWebServices/).

First-pass command pattern:

```sh
GLACIER_HOME=/tmp/glacier-cpsc-live-canary-20261010 \
  ~/w/glacier-lean/.venv/bin/python -m ventures.blocks.feeds.cli sync SOURCE_ID
```

The four `SOURCE_ID` values are the rows below. A second sequential sync of
those same IDs used the cached public responses and the same isolated database.

| Source | First live sync | Canary alerts | Immediate second sync |
| --- | ---: | --- | --- |
| `cpsc_flagged_tariff_codes` | 589 rows | None | 589 rows, `changed: false` |
| `cpsc_rule_codes` | 130 rows | None | 130 rows, `changed: false` |
| `cpsc_registry_template` | 1 template/header record | None | 1 record, `changed: false` |
| `cpsc_recalls` | 10,047 rows | None | 10,047 rows, `changed: false` |

Each first sync returned `changed: true`; each repeat returned `changed: false`
and no alerts. The Recalls API is an auxiliary public recall source; the CPSC
batch pipeline consumes the first three eFiling sources. The detailed feed
block check is in [`ventures/blocks/feeds/CHECK.md`](../blocks/feeds/CHECK.md).
This card's exact row counts, endpoints, first-sync/repeat-sync results, and
scope are captured in
[`evidence/live-feed-canaries-2026-10-10.json`](evidence/live-feed-canaries-2026-10-10.json).
These live feed results supersede the earlier 403 note for CPSC sources. They
do not supersede any 403 notes for unrelated FSIS or OSHA feeds.

## Glacier engine flow runs

On 2026-10-10, all four installed flows were run in an isolated home with the
local FastAPI + DBOS runtime. The captured run IDs, approval states, node
outputs, sample-input limits, and reproductions are in
[`evidence/glacier-engine-flows-2026-10-10.json`](evidence/glacier-engine-flows-2026-10-10.json).

| Flow | Run | Engine result |
| --- | --- | --- |
| `cpsc-feed-refresh` | `8a596dac1ed9` | Done; 589 tariff rows, 130 rule rows, and one template record; stable snapshots, no alerts. |
| `cpsc-code-pages` | `3cdbc40fb427` | Built 589 previews from live CPSC data, then waited at `first-listing-review`; nothing was published. |
| `cpsc-batch-prep` | `d8400fe9cb66` | Ran with one synthetic CSV and local `qwen3:1.7b` second extraction; six required fields matched, one remained uncertain, 89 gaps were reported, no CSV was released, and the flow waited at `review-certify`. This is a runtime demonstration, not a real customer batch. |
| `cpsc-broker-launch` | `220a5b7bce99` | Waited at `lawyer-opinion` as designed; no owner approval was supplied. |

The real-engine run found two flow defects and one data-shape mismatch. The
batch input-ready approval edge lacked the `yes` label, so the engine skipped
draft preparation; that edge is now labeled. The code-page preview initially
reported success with zero rows because it read only top-level feed fields;
the builder now flattens the block's nested `data` records and uses the
published `fetched_at` timestamp for its checked date. The corrected preview
produced all 589 tariff-code pages. A focused non-acceptance test covers the
shared feed record shape. No file under `tests/acceptance/` or
`ACCEPTANCE.md` was changed.

## Official CPSC source page check

On 2026-10-10, the operative CPSC links in the venture README, manifest, lawyer
checklist, ruleset, and source catalog were opened and checked. The eFiling
Importer and Broker resources, Product Registry, Document Library, and FAQ
were reachable. The Document Library listed the current V3 CSV upload
template, the September 2026 HTS guidance, and the citation/testing-exception
workbook. The cited Quick Start Guide, citation/testing guidance PDF, and V4
API specifications PDF were also reachable. The official Recalls API page and
SaferProducts.gov REST endpoint were reachable. These pages support the
venture's data and workflow descriptions; they do not decide whether a
product is regulated or certify a batch.

One URL in an acceptance-only recall fixture,
`https://www.cpsc.gov/Recalls/2026/Example-Heater`, returned an internal error
when opened. It is fixture data, not a production CPSC source link. The
acceptance-owned fixture and tests were left unchanged.

## Test results and owner actions

Using the project interpreter on 2026-10-10:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/cpsc-prep -q
```

Result: **21 passed, 1 skipped**.

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q
```

Result: **21 passed**.

The venture is **ready for owner review**, not live. Paid launch on either
channel still needs the owner's written trade-lawyer opinion. The owner must
choose the broker price, configure live accounts or payment credentials, and
sign any broker contract; each real batch needs review and certification by
the legally responsible, authorized party, and its authorized filer submits
it. The owner also approves any optional code-page publication. See
[LAWYER-QUESTIONS.md](LAWYER-QUESTIONS.md). No customer certificate, paid
transaction, Product Registry upload, certification, filing, account creation,
contract signature, or publication was performed. PH12.9 remains unchanged in
`NORTHSTAR.yaml`; this card updates the venture readiness guide, not the phase
checkpoint.
