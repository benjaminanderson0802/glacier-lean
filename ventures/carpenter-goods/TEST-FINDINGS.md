# Independent commission-flow test findings

Acceptance command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods/tests/acceptance/test_commission_flow.py
```

Result: **3 failed, 3 passed**. The failures below are left active as required; no venture code or acceptance checks were weakened.

## Bugs observed

1. **Etsy amount-column selection is wrong and nondeterministic.** With an Etsy Orders CSV row whose `Order Value` is `$80.00` and `Order Total` is `$95.04` (including `$8.00` shipping and `$7.04` tax), plus a Shopify order total of `$120.96`, the report returned gross sales of `$200.96` instead of `$216.00`. The exporter accepts several amount aliases from a set, so a CSV containing more than one recognized amount column can select the wrong one. The commission agreement requires an explicit eligible amount basis; the flow should choose that named basis or report uncertainty.

2. **Written commission terms and adjustments are ignored.** The terms fixture specified a 12.5% commission on item subtotal after discounts, excluding shipping and tax, with no platform-fee deduction and partial refunds reducing eligible item amount. Etsy's adjusted total and Shopify's `Discount Amount` / `Refunded Amount` were present. The report instead summed the raw mapped totals to `$332.24` rather than the agreement-basis `$220.00`, so the result does not honor discounts, partial refunds, shipping/tax exclusions, or the stated agreement basis. Fees likewise have no effect or explicit treatment in the calculation.

3. **Currency is ignored.** An Etsy row with `Currency=EUR` was accepted as one eligible sale, producing a USD-looking commission total. The flow must reject unsupported or mixed currencies, or leave the amount due uncertain until an agreed conversion basis is supplied.

The full-refund exclusion, rounding example, and local-only/no-automatic-payment checks passed. Shopify's multiline order grouping also ran in the export-fixture check before that check failed on the combined gross amount.

## Fixture source limits

Etsy's [official seller export instructions](https://help.etsy.com/hc/en-us/articles/360000343328-How-to-Download-a-Spreadsheet-of-Your-Sold-Transactions) document the downloadable Orders CSV and some included fields, but do not publish its complete header row. The test therefore records that limitation rather than claiming Etsy's help page documents every fixture header. Shopify's [official order-export documentation](https://help.shopify.com/en/manual/fulfillment/managing-orders/exporting-orders) lists the order CSV headers and explains blank continuation rows for multi-item orders.
