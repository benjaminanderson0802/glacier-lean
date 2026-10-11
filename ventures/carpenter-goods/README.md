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

Export Etsy's **Orders** CSV and Shopify's orders CSV to `incoming/etsy-orders.csv` and `incoming/shopify-orders.csv`. The importer recognizes order ID (`Order ID`, `Name`, `Order`, or `Order Number`), payment status (`Order Status`, `Financial Status`, `Payment Status`, or `Status`), and order total (`Order Total`, `Total Order Value`, `Order Value`, or `Total`). Shopify's documented export can use multiple lines for multi-item orders; the importer groups its line-item rows by order and reads the order total once. Only rows whose status is exactly **paid** count. Unpaid, refunded, partial, canceled, duplicate, invalid, or missing-total rows are excluded and listed. The Etsy and Shopify instructions are documented in [Etsy's order CSV help](https://help.etsy.com/hc/en-us/articles/360035753053-How-Do-I-Download-My-Etsy-Data) and [Shopify's order export guide](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders).

Run the **Track agreed furniture commissions** flow, or:

```sh
python ventures/carpenter-goods/scripts/listing_prep.py commissions \
  --etsy-csv "$GLACIER_HOME/ventures/carpenter-goods/incoming/etsy-orders.csv" \
  --shopify-csv "$GLACIER_HOME/ventures/carpenter-goods/incoming/shopify-orders.csv" \
  --rate-file "$GLACIER_HOME/ventures/carpenter-goods/incoming/commission-terms.json" \
  --output "$GLACIER_HOME/ventures/carpenter-goods/reports/commission.json"
```

The report calculates the agreed rate against exported order totals. Confirm in the signed agreement whether tax, shipping, discounts, platform fees, refunds, and chargebacks affect the eligible amount. Compare totals with the platform settlements before any invoice or payment. The report moves no money. Keep customer exports local, restrict access, and remove them within 30 days after the job closes unless the customer asks to keep them.

## Current limits

The live Glacier listing command and output check were exercised with disposable synthetic inputs. The official Shopify export layout has a public-schema benchmark using synthetic order values. No live Etsy/Shopify merchant export, current comparable-sale record, signed agreement, or public listing was used. The commission flow remains blocked by Glacier's requirement for an acceptance check; this card cannot author that independent check. See [PROOF.md](PROOF.md) for run evidence and limits.
