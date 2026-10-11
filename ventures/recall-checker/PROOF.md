# Proof — Recall checker

## Acceptance checks

From the repository root:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s ventures/recall-checker/tests -v
/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only recall-checker --dry-run
```

The focused suite checks exact barcode citations, ambiguous model handling, the result vocabulary, empty feeds, batch CSV results, distinct source-linked HTML pages, the MV3 manifest and its restricted permissions, and API request validation. The 2026-10-10 isolated run reports **10 passed, 1 failed**: the venture-specific example expects `no match in ...`, while the venture-wide required wording is `no match found in ...`. Claim `claim-ph12-12-recall-output-vocabulary` records this conflict; the check was not modified. Manifest dry-run confirms all three flows and their schedule against Glacier's current node catalog.

## Real public sources and Glacier

The source registry uses official CPSC, NHTSA, FDA and FSIS endpoints through `ventures.blocks.feeds`. Live-source refresh and a running-Glacier dry-run have not been completed for this local recall-checker flow. Owner update on 2026-10-10: the separate Apify recall Actor is deployed and the Chrome Web Store developer account is registered. No marketplace crawl, paid API, or real portal submission was performed.

## Accuracy gate and owner steps

The spec requires 500 known-recalled and 500 known-clean labeled items, with at most 1% false no-match, and owner review of the first 50 pages. That labeled set is not present in the assigned card inputs. The implementation keeps borderline or incomplete-feed cases uncertain; this does not substitute for the benchmark. Chrome Web Store submission, first-page review before public hosting, and plan/test-key configuration remain owner steps.
