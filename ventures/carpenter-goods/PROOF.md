# Proof — Carpenter's goods

## Fixture acceptance

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods -q
```

Result: **9 passed**.

The suite covers source-linked same-category completed-sale validation and median pricing, uncertain/no-price behavior, paid-only commission calculations, invalid rates, venture manifest instructions, product-sheet CSV to Etsy/Shopify draft generation, Etsy and Shopify order-export CSV commission summaries, and agreement/template presence. The CSV E2E cases invoke the command-line workflow using synthetic fixtures. They do not prove current market pricing, real platform export compatibility, or live shop behavior.

## Manifest validation

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run
```

`~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run` — both modified flow manifests validated against the node catalog.

## Live verification status

Started the real FastAPI backend with disposable homes, installed both current flows (`carpenter-prepare-listing`: `c345a47e` and `b82a8fc4`; second listing smoke: installed into a fresh home), and exercised the API with synthetic records. The installer resolved the `{repo}` working directory, so the previous claim's exact failure did not recur in this smoke run. The commission flow was refused with HTTP 400: “This goal has no check yet. Add a way to check it is done before running it.” I stopped there because adding its judging check requires an independent check author under I-04. The listing flow accepted one input approval in the fresh retry but still marked `prepare_draft` and downstream nodes skipped; its required output check failed because `drafts/listing.json` had not been created. The first listing smoke sent duplicate approvals while the backend remained in a waiting state; a fresh backend run with each approval sent only once reproduced the skipped-node result. This runtime behavior needs investigation in the runtime lane. Neither flow counts as a successful live run.

No Etsy/Shopify account, live export, signed agreement, current comparable-sales record, public listing, invoice, or payment was used or made. Owner signing, account access, publication, and payment remain manual.

The broader `~/w/glacier-lean/.venv/bin/python -m pytest ventures -q` attempt did not collect: unrelated recall-actor and utility-audits tests raised `ModuleNotFoundError` for `src.sources` and `scripts.utility_audit`. This card did not change those paths.

The commission-flow acceptance-check gap and the reproduced listing-flow transition failure need claims routed to the independent verifier/runtime lane. This card is scoped to `ventures/**`, so those claims were not filed here.

## Acceptance still outstanding

Do not mark PH12.20 done based on fixture tests alone. Passing runtime flows, owner-provided current records, an independent commission acceptance check, and independent spec review remain outstanding. Current owner tasks are grouped into two steps in `venture.json`: agree and supply; review and publish.
