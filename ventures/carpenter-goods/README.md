# Carpenter's goods — ready for owner and maker inputs

This venture prepares private Etsy and Shopify listing drafts from a maker-confirmed product sheet and source-linked completed sales. It can also calculate a commission summary from owner-exported order CSVs and the rate in the written agreement. The tools do not sign agreements, connect to shop accounts, answer buyers, handle orders, publish listings, invoice, charge, or move money.

## Owner steps

There are two owner sittings; the detailed links, clicks, file paths, and time estimates are in [OWNER-STEPS.md](OWNER-STEPS.md).

1. **Meet with the carpenter (about 30–60 minutes, plus gathering records):** finish and both sign the prepared [commission agreement](agreement/commission-agreement.md), provide maker-confirmed product facts and local photo paths, at least three current source-linked completed sales, and any needed order exports. Georgia sales-tax registration applicability remains **uncertain — please check** with the linked DOR guidance before the first physical-goods sale.
2. **Review and publish (about 15–30 minutes per first product):** review Glacier's Etsy and Shopify drafts, facts, photos and comparable-based suggested price, choose the final price, and publish manually only if approved.

The short [signing worksheet](agreement/commission-summary.md) accompanies the full agreement. Both parties must fill and review all marked terms and sign themselves. These templates are not legal advice. Glacier never signs or publishes.

The human-readable [Etsy listing draft](drafts/etsy-listing-draft.md), [Shopify listing draft](drafts/shopify-listing-draft.md), and [data request](OWNER-DATA-REQUEST.md) are prefilled with known workflow details. Product facts, legal terms, and price stay blank/uncertain because no real maker or sales records were supplied. The sample product and sale values under `tests/` are synthetic and must never be used as listings or pricing evidence.

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

Venture acceptance and regression checks pass, and both flows validate for installation. Live Glacier listing-engine proof used disposable synthetic inputs only; it did not create a shop listing. The independent signed-terms commission acceptance now passes. No live Etsy/Shopify merchant export, real comparable-sale record, signed agreement, or public listing was used. The venture is ready for the owner and carpenter to provide real inputs and perform the two manual approval sittings. See [PROOF.md](PROOF.md) for commands and evidence boundaries.
