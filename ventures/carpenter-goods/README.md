# Carpenter's goods

This venture prepares private Etsy and Shopify listing drafts from a maker-confirmed product sheet and source-linked completed sales. It can also calculate a commission summary from owner-exported order CSVs and the rate in the written agreement. The tools do not sign agreements, connect to shop accounts, answer buyers, handle orders, publish listings, invoice, charge, or move money.

## Owner steps

1. **Sign, supply, and review.** Agree the commission terms with the carpenter and both sign the agreement; provide maker-confirmed product facts, local photo paths, at least three current source-linked completed sales, and any order exports. When Glacier prepares the draft, review every fact, photo, comparable, and price, then publish manually only if you approve. Glacier does not sign or publish.

The short [plain-language agreement summary](agreement/commission-summary.md) explains the terms; the signed full agreement controls if they differ. The agreement templates are not legal advice. Have both parties review all blanks and terms; seek legal advice if needed. Glacier never signs.

## Preparing listing drafts

Copy the [product sheet CSV template](templates/product-sheet-template.csv) to `$GLACIER_HOME/ventures/carpenter-goods/incoming/product-sheet.csv` and fill exactly one row. `templates/product-sheet.csv` is kept as a compatible copy of the same header-only template. Use semicolons between materials and between local photo paths. Keep photos on the local machine. The `comparables.json` file is a list of objects with `source_url`, `category`, `completed: true`, `sold_price`, and `sold_date` (`YYYY-MM-DD`). Duplicate URLs, invalid prices/dates, stale or future sales, incomplete sales, and category mismatches are rejected. Fewer than three eligible comparisons leave the suggested price blank and the result **uncertain — please check**. No market data is scraped or invented.

Run the **Prepare a handmade furniture listing** flow, or from the repository root run:

```sh
python ventures/carpenter-goods/scripts/listing_prep.py prepare \
  --product-csv "$GLACIER_HOME/ventures/carpenter-goods/incoming/product-sheet.csv" \
  --comparables "$GLACIER_HOME/ventures/carpenter-goods/incoming/comparables.json" \
  --output "$GLACIER_HOME/ventures/carpenter-goods/drafts/listing.json"
```

The result contains separate Etsy and Shopify copy and stays unpublished. Photos are references only; edits and uploads are manual.

## Commission summary

Export Etsy's **Orders** CSV and Shopify's orders CSV to `incoming/etsy-orders.csv` and `incoming/shopify-orders.csv`. The importer recognizes order ID (`Order ID`, `Name`, `Order`, or `Order Number`) and payment status (`Order Status`, `Financial Status`, `Payment Status`, or `Status`). With no `eligible_amount` in the terms file, it uses an explicit order-total column in this fixed precedence: `Order Total`, `Total Order Value`, `Total`, then `Order Value`. Shopify's documented export can use multiple lines for multi-item orders; the importer groups its line-item rows by order and reads the order total once. Paid orders count; unpaid, fully refunded, canceled, duplicate, invalid, and missing-total rows are excluded and listed. Partially refunded orders count only with the supported refund rule and an exported item-refund amount. The Etsy and Shopify instructions are documented in [Etsy's order CSV help](https://help.etsy.com/hc/en-us/articles/360035753053-How-Do-I-Download-My-Etsy-Data) and [Shopify's order export guide](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders).

Run the **Track agreed furniture commissions** flow, or:

```sh
python ventures/carpenter-goods/scripts/listing_prep.py commissions \
  --etsy-csv "$GLACIER_HOME/ventures/carpenter-goods/incoming/etsy-orders.csv" \
  --shopify-csv "$GLACIER_HOME/ventures/carpenter-goods/incoming/shopify-orders.csv" \
  --rate-file "$GLACIER_HOME/ventures/carpenter-goods/incoming/commission-terms.json" \
  --output "$GLACIER_HOME/ventures/carpenter-goods/reports/commission.json"
```

Put the agreed rate in `commission-terms.json` as a fraction (`0.125` means 12.5%). Name the basis with `eligible_amount`: the calculator supports an order total, or an item subtotal after discounts. For an item-subtotal agreement, Etsy's `Order Value` and Shopify's `Subtotal` are used, then `Discount Amount` and the refunded item amount are deducted. Example:

```json
{
  "rate": 0.125,
  "eligible_amount": "item subtotal after discounts, excluding shipping and sales tax",
  "include_shipping": false,
  "include_sales_tax": false,
  "deduct_platform_fees": false,
  "refund_rule": "reduce eligible amount by the refunded item amount"
}
```

When using an order-total basis, set `include_shipping` and `include_sales_tax` to match the signed terms; when either is `false`, that amount is removed from the exported total. Platform fees are left in the eligible amount unless `deduct_platform_fees` is `true`; then the export must include a fee value. The supported partial-refund rule above uses Shopify's `Refunded Amount`; Etsy's available `Adjusted Order Total` reduction is used as its refund amount. If a field required by the terms is missing, the report is **uncertain — please check**. Canceled and fully refunded orders do not count. Only USD orders are calculated; unsupported or mixed currencies make the amount due uncertain, with no exchange rate guessed. A rate-only legacy terms file uses the order-total default and the report names that basis explicitly.

Compare totals with platform settlements and the signed agreement before any invoice or payment, including any return or chargeback rules not expressed in the supported terms fields. The report moves no money. Keep customer exports local, restrict access, and remove them within 30 days after the job closes unless the customer asks to keep them.

## Current limits

The live Glacier listing command and output check were exercised with disposable synthetic inputs. The official Shopify export layout has a public-schema benchmark using synthetic order values. No live Etsy/Shopify merchant export, current comparable-sale record, signed agreement, or public listing was used. The commission flow remains blocked by Glacier's requirement for an acceptance check; this card cannot author that independent check. See [PROOF.md](PROOF.md) for run evidence and limits.
