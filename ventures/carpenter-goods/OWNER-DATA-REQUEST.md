# Carpenter goods — prefilled data request

Give this form to the carpenter during the agreement meeting. Fill only from the owner or maker's records. **Do not use test fixtures as real facts.** Keep this file and all source exports/photos local.

## A. Maker-confirmed product facts

Copy `templates/product-sheet-template.csv` to:

```text
$GLACIER_HOME/ventures/carpenter-goods/incoming/product-sheet.csv
```

Fill one row for each product. Use semicolons between materials and between local photo paths.

| CSV field | Supply this value |
| --- | --- |
| `product_id` | Maker's stable SKU or another unique ID: **[maker to supply]** |
| `name` | Exact product name: **[maker to supply]** |
| `category` | Plain product category: **[maker to supply]** |
| `description` | Maker-confirmed description; avoid unsupported claims: **[maker to supply]** |
| `pickup_area` | Exact pickup area, or leave blank if pickup is not offered: **[owner/maker to confirm]** |
| `materials` | Actual materials, separated by semicolons: **[maker to supply]** |
| `dimensions` | Measurements with units: **[maker to supply]** |
| `condition` | Actual condition (for example, new or used): **[maker to supply]** |
| `photos` | Local paths to original photos, separated by semicolons: **[owner/maker to supply]** |

Attach a short written confirmation from the maker that the facts and photos may be used in the shop listings. State any restrictions in the signed agreement. Do not put photo files in a public link.

## B. Comparable completed sales for price guidance

Create `$GLACIER_HOME/ventures/carpenter-goods/incoming/comparables.json` in this shape, replacing every placeholder with a real source record:

```json
[
  {
    "source_url": "[direct URL to completed sale or source record 1]",
    "category": "[same exact category as the product sheet]",
    "completed": true,
    "sold_price": "[actual amount as a decimal string]",
    "sold_date": "[YYYY-MM-DD]"
  },
  {
    "source_url": "[direct URL to completed sale or source record 2]",
    "category": "[same exact category as the product sheet]",
    "completed": true,
    "sold_price": "[actual amount as a decimal string]",
    "sold_date": "[YYYY-MM-DD]"
  },
  {
    "source_url": "[direct URL to completed sale or source record 3]",
    "category": "[same exact category as the product sheet]",
    "completed": true,
    "sold_price": "[actual amount as a decimal string]",
    "sold_date": "[YYYY-MM-DD]"
  }
]
```

Use same-category sales that actually completed and are current under the workflow's validation window. Asking prices, `example.test` links, and generated sample amounts are not sales evidence. The calculator uses the median of eligible records; fewer than three means **uncertain — please check** and no suggested price.

## C. Commission terms for the signed agreement

Fill this only after Seller and Maker agree and sign the full agreement. Copy the agreed values exactly into `$GLACIER_HOME/ventures/carpenter-goods/incoming/commission-terms.json`:

```json
{
  "signed": false,
  "rate": "[agreed percent as a fraction; e.g. 12.5% is 0.125]",
  "eligible_amount": "[exact signed basis: order total OR item subtotal after discounts]",
  "include_shipping": "[true or false per signed terms]",
  "include_sales_tax": "[true or false per signed terms]",
  "deduct_platform_fees": "[true or false per signed terms]",
  "refund_rule": "[signed rule: exclude/reverse refunded orders OR reduce eligible amount by refunded item amount]",
  "rounding": "round half up to two currency decimals"
}
```

Replace each bracketed value with a JSON value of the right type (number for `rate`, string for `eligible_amount`/`refund_rule`, booleans for the three flags). Keep `signed` false until both have signed, then change it to `true`; the report otherwise stays uncertain. The rounding line is the calculator's supported rule and must be accepted in the signed agreement. This form deliberately chooses no rate or amount basis for the parties. If the agreement uses unsupported treatment for fees, returns, or chargebacks, the result stays uncertain until the workflow can represent it.

## D. Existing order exports (only if calculating earned commission)

- Etsy: [Etsy Shop Manager](https://www.etsy.com/your/shops/me/dashboard) → **Settings** → **Options** → **Download Data** → **Orders** → choose **CSV Type**, **Month**, **Year** → **Download CSV**. Save as `$GLACIER_HOME/ventures/carpenter-goods/incoming/etsy-orders.csv`. Official help: [download sold transactions](https://help.etsy.com/hc/en-us/articles/360000343328-How-to-Download-a-Spreadsheet-of-Your-Sold-Transactions).
- Shopify: [Shopify Admin](https://admin.shopify.com/) → **Orders** → **Export** → choose orders/date range → **CSV** → **Export orders**. Save as `$GLACIER_HOME/ventures/carpenter-goods/incoming/shopify-orders.csv`. Official help: [export orders and CSV fields](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders).

Shopify's export can use multiple rows per order. Preserve the CSV as downloaded; the importer groups line-item rows by order. Exports can include customer personal data. Share only what the signed agreement requires, keep it on owner-controlled storage, and delete it within 30 days after the job closes unless the customer asks to retain it.
