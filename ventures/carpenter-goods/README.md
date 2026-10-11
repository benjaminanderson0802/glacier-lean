# Carpenter's goods

This venture prepares private Etsy and Shopify listing drafts from a maker-confirmed product sheet and source-linked completed sales. It can also calculate a commission summary from owner-exported order CSVs and the rate in the written agreement. The tools do not sign agreements, connect to shop accounts, answer buyers, handle orders, publish listings, invoice, charge, or move money.

## Owner steps

1. **Agree and supply.** Fill in [the commission agreement](agreement/commission-agreement.md) with the carpenter, decide what order amount the commission applies to, and have both people sign it themselves. Fill [the product sheet](templates/product-sheet.csv) with maker-confirmed facts and local photo paths. Supply at least three same-category completed sales from the last 365 days, with dates and source URLs, in `incoming/comparables.json`. For a commission report, export Etsy and Shopify order-level CSVs and place them at `incoming/etsy-orders.csv` and `incoming/shopify-orders.csv`. Use the filled agreement's decimal rate in `incoming/commission-terms.json`. Obtain exports yourself from the [Etsy shop dashboard](https://www.etsy.com/your/shops/me/dashboard) or [Shopify admin](https://admin.shopify.com/).
2. **Review and publish.** Review every generated fact, photo path, comparable, price, and platform draft. If correct, publish manually in the Etsy shop or Shopify admin. Glacier will not publish.

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

Export order-level CSVs (one order per row) using the headers in `templates/etsy-orders.csv` and `templates/shopify-orders.csv`, or supported equivalent headers: order ID (`Order ID`, `Name`, `Order`, or `Order Number`), payment status (`Order Status`, `Financial Status`, `Payment Status`, or `Status`), and order total (`Order Total`, `Total Order Value`, `Order Value`, or `Total`). Save the exports under `incoming/etsy-orders.csv` and `incoming/shopify-orders.csv`. Only rows whose status is exactly **paid** count. Unpaid, refunded, partial, canceled, duplicate, invalid, or missing-total rows are excluded and listed. Use an order-level export to avoid counting line items twice.

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

CSV workflow and agreement files are fixture-tested only. No live Etsy/Shopify export, current comparable-sale record, signed agreement, public listing, or real runtime workflow has been verified. The previously observed runtime working-directory issue is tracked in [claim CLM-PH12-20-CWD-REPO](../../vault/claims/2026-10-10-ph12-20-command-cwd-repo-placeholder.md); the installer adjustment has not yet had a fresh real-runtime smoke check. See [PROOF.md](PROOF.md) for exact evidence and limits.
