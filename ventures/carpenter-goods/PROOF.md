# Proof — Carpenter's goods

## Fixture acceptance

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods -q
```

Result after adding the acceptance-discoverable template filename: **10 passed, 2 xpassed**. The two xpasses are the agreement and product-sheet acceptance checks whose `awaiting builder` markers remain in place; they pass when run normally and with `--runxfail`.

The suite covers source-linked same-category completed-sale validation and median pricing, uncertain/no-price behavior, paid-only commission calculations, invalid rates, venture manifest instructions, product-sheet CSV to Etsy/Shopify draft generation, Etsy and Shopify order-export CSV commission summaries, and agreement/template presence. The acceptance check was also run directly with xfail disabled:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods/tests/acceptance/test_v_carpenter2.py::test_product_sheet_csv_generates_etsy_shopify_drafts_without_publishing -q --runxfail
```

Result: **1 passed**. The discoverable `templates/product-sheet-template.csv` has the same header as the compatible `templates/product-sheet.csv`; both are templates only. The CSV E2E cases invoke the command-line workflow using synthetic fixtures. They do not prove current market pricing, real platform export compatibility, or live shop behavior.

## Manifest validation

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run
```

`~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run` — both modified flow manifests validated against the node catalog.

## Real Glacier engine run

Started the actual FastAPI/DBOS engine with a disposable `GLACIER_HOME`, installed the two manifest flows with `ventures/install_all.py`, and ran **Prepare a handmade furniture listing** through the local engine API. Inputs were synthetic fixture records copied into that temporary home. No network requests to Etsy or Shopify were made.

- Temporary home: `/tmp/carpenter-live-ywr6rqqy`
- Installed flow registrations: listing `2d3f8892`; commissions `cffb1e2f`
- Listing run ID: `c2b14bf4f01f`
- Owner input approval: approved only to let the synthetic fixture continue.
- Engine state at the review gate: `waiting_on=approve_listing`; `owner_input_ready`, `prepare_draft`, and `draft_ready` were `done`.
- Command output: `{"result":"match","output":"/tmp/carpenter-live-ywr6rqqy/ventures/carpenter-goods/drafts/listing.json","published":false}`. The generated fixture draft had Etsy and Shopify titles `Live edge walnut coffee table`, suggested price `$425.00` (median of synthetic `$400/$425/$450` comparables), and `published: false`.
- Check output: `draft_ready: yes`; the flow's required output check passed.
- Backend log: `POST /api/environments/carpenter-prepare-listing/run` returned 200; one `POST /api/runs/c2b14bf4f01f/approve` returned 200; run polling showed `prepare_draft=done`, `draft_ready=done`, and then `waiting_on=approve_listing`. The engine shut down cleanly.

The real run exposed a flow wiring defect: `owner_input_ready` emits a `yes` branch, but its edge to `prepare_draft` had no label, so the engine skipped the listing command. The edge now has label `yes`, and `tests/test_flow_runtime.py::test_owner_input_approval_yes_edge_runs_listing_command` guards it. The live run above verifies the command and output check after that fix. The run remains at the real owner review gate; I did not approve the draft or publish it.

The commission flow installation succeeded, but starting it through the engine returned HTTP 400: “This goal has no check yet. Add a way to check it is done before running it.” I did not create a judging check because I-04 requires an independent author. The commission CLI remains fixture-tested, but a real engine commission run is an outstanding verifier handoff, not an owner-only action.

## Public-source export benchmark

Verified the Etsy and Shopify export guidance against the platforms' official help pages: [Etsy order CSV instructions](https://help.etsy.com/hc/en-us/articles/360035753053-How-Do-I-Download-My-Etsy-Data) and [Shopify order export format](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders). Shopify documents that multi-item orders occupy multiple CSV lines and that many order fields are blank on continuation lines. The importer now groups these Shopify rows by order and carries forward the order ID; conflicting totals are not summed or guessed.

`tests/test_official_export_benchmark.py::test_shopify_multiline_order_export_counts_each_paid_order_once` uses Shopify's public header/layout documentation with invented order IDs and amounts, not public transaction records. It checks one paid multiline order is counted once and a refunded order is excluded. This does not establish compatibility with a real merchant export. No official public source located for public, current completed-sale records suitable for pricing; the venture still requires the owner to provide three current, source-linked completed sales.

No Etsy/Shopify account, live merchant export, signed agreement, current comparable-sale record, public listing, invoice, or payment was used or made. Owner signing, price choice, account access, draft approval, publication, and payment remain manual.

The broader `~/w/glacier-lean/.venv/bin/python -m pytest ventures -q` attempt did not collect: unrelated recall-actor and utility-audits tests raised `ModuleNotFoundError` for `src.sources` and `scripts.utility_audit`. This card did not change those paths.

## Acceptance still outstanding

PH12.20 remains unverified. The listing command and check ran in the real engine, but the full listing run awaits the owner review gate. The commission flow cannot start until an independent author supplies its acceptance check; this is an uncompleted non-owner release gate. Real merchant exports, three current source-linked sales, and independent spec review also remain outstanding. The owner's plain-language action is listed in `README.md`.
