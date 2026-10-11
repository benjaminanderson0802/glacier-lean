# Proof — Carpenter's goods

## Acceptance and regression checks

After the signed-terms correction, the independent commission acceptance suite passes. The suite checks paid-order calculations against Etsy seller CSV fields and Shopify's documented CSV headers/continuation rows; agreement basis, discounts, shipping, tax, fees, refunds, rounding, currency, and local-only behavior. Its order values and IDs are synthetic.

Commands and results for this card:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods ventures/tests
```

**59 passed, 2 subtests passed.** This includes the independent commission acceptance checks, venture regressions, and adjacent ventures board.

```sh
~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run
```

Both flow manifests validate against the node catalog. The commission flow now has a human acceptance gate: the owner compares the report with the signed terms and platform settlements before relying on an amount. This is a check of that run's actual report; it does not authorize Glacier to invoice, contact anyone, charge, or transfer money.

## Live Glacier listing run

An earlier real FastAPI/DBOS run installed both flows and ran **Prepare a handmade furniture listing** using disposable synthetic inputs in `/tmp/carpenter-live-ywr6rqqy` (listing run `c2b14bf4f01f`). The product title and `$425.00` median were synthetic fixture values, not market evidence. The local output check passed with `published: false`, then the run waited at the owner's review gate. No Etsy/Shopify request or publication occurred.

That run exposed a missing `yes` label on `owner_input_ready → prepare_draft`; it is fixed and covered by `ventures/carpenter-goods/tests/test_flow_runtime.py::test_owner_input_approval_yes_edge_runs_listing_command`.

## Live Glacier commission run

Installed and started **Track agreed furniture commissions** through the real FastAPI/DBOS engine in disposable `GLACIER_HOME` `/tmp/carpenter-commission-live-g0t0iq6e`. Run `a185534d84da` used synthetic Etsy and Shopify CSV rows and explicitly synthetic signed-term settings. The generated report was `match`, 2 eligible orders, `$300.00` gross, and `$30.00` at the synthetic 10% rate. The run then stopped at `waiting_on=check-0` with the owner verification question; `verified` remained null and the gate was deliberately left unapproved. These values are a runtime smoke only, not actual sales or an amount due.

A first smoke omitted shipping and tax columns while the terms excluded those fields. The actual engine correctly returned **uncertain — please check**, listed both missing-field reasons, and set no amount due. A fresh smoke with explicit zero-valued shipping/tax columns produced the synthetic match above. This confirms missing term data remains uncertain rather than guessed.

## Shared test board status

`bash setup/run_core_tests.sh` completed but the shared board did not pass: **896 passed, 5 failed, 1 skipped, 5 warnings**. It reported failures in `tests/test_home_route.py`; a focused reproduction from `glacier/backend` gave **3 failed, 2 passed**. The observed mismatches were `/api/home` reporting 38 `need_you` items in an empty state (expected 0), 41 instead of 3 for the seeded case, and a missing `needs_you[0].ref.run_id`. These are outside the carpenter venture files and were not changed here. The same board's web build checks passed, but `node e2e/core.spec.mjs` could not launch because Playwright's Chromium executable is absent. Its bootstrap also attempted `pip --user install uv`, which the host rejected under PEP 668; `uv` was unavailable, so setup continued using the existing environment.

`bash setup/live_codex_check.sh` returned exit code 0 but printed repeated `JSONDecodeError: Expecting value` traces while parsing the live run result. The shared core/live checks therefore remain an integration gate; PH12.20 is left `in_progress` in `NORTHSTAR.yaml` even though the carpenter venture itself is ready for its two owner sittings.

## Export source and data limits

- [Etsy's official sold-transaction CSV instructions](https://help.etsy.com/hc/en-us/articles/360000343328-How-to-Download-a-Spreadsheet-of-Your-Sold-Transactions) document its Orders/Order items export flow and available data, but not a complete CSV header row.
- [Shopify's official order export guide](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders) documents CSV headers and multiple rows for orders with multiple line items. The importer groups continuation rows by order; the independent test uses synthetic values.
- No official public source of current completed sale records suitable for these products was identified. The maker/owner must supply at least three current, same-category, source-linked completed sales. Fewer than three eligible records produce **uncertain — please check** and no suggested price.

## Prepared owner handoff

[`OWNER-STEPS.md`](OWNER-STEPS.md) has two combined sittings with exact links/clicks, local file paths, and time estimates. The prepared [commission agreement](agreement/commission-agreement.md), [signing worksheet](agreement/commission-summary.md), [data request](OWNER-DATA-REQUEST.md), and [Etsy](drafts/etsy-listing-draft.md)/[Shopify](drafts/shopify-listing-draft.md) drafts use only known workflow details. Names, commission rate, product facts, photos, and price remain blank or uncertain because none were supplied from real records. The sample data under `tests/` is synthetic and is not an owner listing or price source.

No live merchant export, signed agreement, real comparable sale, or public listing was used. Owner signatures, final price choice, Georgia tax applicability check/registration if required, listing approval, and publication remain manual. No invoice or payment was created.
