# CPSC data prep proof

## Drift check and acceptance

- Checkpoint: PH12.9. PH12 depends on PH5 and PH9; wave 6 explicitly assigns
  this venture as parallel-safe.
- Properties/metrics: P-CONTROL and P-USABLE; M-VERIFIED and M-INTERVENE.
- Existing tools / I-01: CPSC provides a Product Registry, a bulk-upload CSV
  template and an API for certificate data. Those support registry management
  and import, but do not cover this card's document extraction, cited source
  review, gap reporting, two-engine agreement, and local customer certification
  workflow. The venture uses that official template and the shared OSS blocks;
  its custom code is glue for this workflow and never replaces the registry or
  submits data. Sources: [CPSC Product Registry](https://www.cpsc.gov/eFiling-CPSC-Product-Registry)
  and [eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library).
- Acceptance: output follows the current template columns, carries cited source
  pages, reports blanks as gaps, blocks missing required fields,
  mismatches/unknown codes/unapproved customer certification, and never
  submits to CPSC.

## Checks run

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/cpsc-prep/tests
```

Output: `13 passed in 0.04s`.

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m py_compile ventures/cpsc-prep/scripts/cpsc_prep.py ventures/cpsc-prep/tests/test_pipeline.py
```

Output: exit 0, no compile errors.

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only cpsc-prep --dry-run
```

Output: all four manifest flows validated: `cpsc-batch-prep`,
`cpsc-broker-launch`, `cpsc-feed-refresh`, and `cpsc-code-pages`; exit 0.

## Real Glacier registration/run

Started `npm run live` from `glacier/web` under
`flock /tmp/glacier-heavy.lock`. The real backend started successfully in a
temporary Glacier home. `ventures/install_all.py --only cpsc-prep` registered
all four flows; each `PUT /api/environments/{flow}` returned `saved: true`.

The real `cpsc-batch-prep` dry run failed at `prepare-draft` with:

```text
cpsc-prep: CPSC prep requires the reader, rules, and feeds blocks from ventures.blocks
```

Those blocks are assigned to parallel PH12.4–PH12.6 cards and are not merged in
this checkout. No claim is made that the CPSC batch ran on public data. The
separate real Glacier `cpsc-broker-launch` flow reached its durable wait:

```text
status: waiting
waiting_on: lawyer-opinion
node_states: lawyer-opinion=waiting, first-contract=pending, ready=pending
```

It was left waiting; no legal opinion or contract was approved or signed.
Glacier's temporary live home was removed when the live process stopped.

## External source check

CPSC's [eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library)
currently lists the official bulk upload template and user guide, plus a
September 14, 2026 HTS flagging list. The feeds block must expose these current
sources and canaries before the real-data release check can pass.

## Remaining release checks

The shared reader, rules, feeds, customer, and mail release checks have not
been demonstrated because those block implementations are not present here.
The real second-engine path also needs a configured local Ollama model via
`GLACIER_OLLAMA_URL` and `GLACIER_LOCAL_MODEL`; absent that, the pipeline leaves
fields uncertain. Stripe/customer sandbox purchase and signature checks are
not done. Screenshots in `evidence/ventures/` and the PH12.9 status update are
deferred to the integrator after the blocks merge and a successful live run.

Exact shared-block functions are listed in `README.md` and `venture.json`.

## I2 integration update (2026-10-10)

B1's reader/rules blocks and B2's feeds/deadlines blocks are now present in the I2 worktree. The original missing-block error above describes the earlier branch state. The integrated installer dry-run validated all four CPSC flows. The current feed registry still lacks the three CPSC list/template IDs, and the flat venture fields do not satisfy the merged `cpsc_efiling.json` ruleset; see `../AUDIT-wave2.md` and claim `CLM-PH12-22-CPSC-INTEGRATION-GAP`. Missing source IDs now stop with an uncertain result instead of an uncaught lookup error. No CPSC batch or public-source release check was run because the shared heavy-job slots exceeded the worker backstop. Do not treat PH12.9 as released.
