# Proof — Recall Actor

## Acceptance checks

From the repository root, the independent Recall Actor checks pass with their xfail markers ignored:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/recall-actor/tests/acceptance/test_v_recallfix.py -q --runxfail
```

Result: **3 passed, 1 skipped**. The passing checks cover openFDA's valid empty response, bounded CPSC phrase lookup with RecallID deduplication, and the six-field Actor output/schema. The live Rock 'n Play canary is the skipped check.

The complete venture suite also passes:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/recall-actor -q
```

Result: **10 passed, 2 skipped, 3 xpassed, 3 subtests passed**. The xpassed checks are independent acceptance checks whose `awaiting builder` markers are still present; no acceptance files were changed.

## What changed

Name-only lookups use up to three independent CPSC probes: the full `ProductName`, a shortened `RecallTitle`, and an apostrophe variant of shortened `ProductName`. This includes the shortened `Rock 'n Play` phrase that matched in the previously confirmed live run. The dataset schema keeps Apify's `fields` declaration and also exposes the six result fields through `properties` for consumers using that interface. The Actor pushes the complete result record.

## Fixture versus live evidence

The commands above use fixtures and a mocked source client for the acceptance assertions; they do not call CPSC or verify deployment. The opt-in `RECALL_LIVE=1` canary was not run for this card. Per the owner-provided project context, a prior live Rock 'n Play run confirmed a CPSC match; this proof file does not treat that prior run as new evidence or claim a current live result.

The owner remains responsible for Actor account, payout, event-price and run-charge settings, and any publication decision. The tests do not perform signing, payment setup, filing, or publication.
