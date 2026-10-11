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

## Real Glacier and remaining launch evidence

An earlier real Glacier attempt in the pre-integration worktree registered the
four CPSC flows. The batch flow stopped because its reader, rules, and feeds
blocks were not available in that worktree; the separate broker-launch flow
waited at the lawyer-opinion approval. That result is historical and does not
describe the current checkout. The block implementations are now present.

The current venture suite confirms the feeds block loads, the three CPSC
source IDs are registered, and the venture's field adapter can pass the
fixture to the merged rules checker. The old wave-2 note about missing source
IDs and unadapted fields is superseded by the current checkout. However, no
current real-Glacier end-to-end batch was run in this card. No customer
certificate batch, live independent second-engine extraction, customer
certification, Product Registry upload, or filing has been demonstrated.

Paid launch for either customer channel and broker-portal onboarding remain
gated on the owner's written trade lawyer opinion covering this exact service
and fee model. The owner must also sign any broker contract and create/configure
accounts or payment credentials. The legally responsible and authorized
certifier reviews and certifies each batch; the authorized filer submits
through their own route. Public code-page publication also remains behind its
explicit owner approval flow. Glacier does not perform these actions. See
[LAWYER-QUESTIONS.md](LAWYER-QUESTIONS.md) for the counsel checklist.

The evidence supports working official source canaries and fixture-tested
pipeline logic. It does not support calling PH12.9 released or the venture
launch-ready while the legal opinion, real batch verification, configured
independent engine, and owner-only steps remain outstanding.
