# Acceptance — V-CARPENTER2

1. Provide a commission agreement template with clearly marked blanks and a one-page plain-language summary; include a `not legal advice` note.
2. Provide a product-sheet CSV template and prepare Etsy and Shopify listing drafts from its rows.
3. Do not publish listings, edit shops, handle buyer replies, or change inventory without an explicit owner step.
4. Calculate commission summaries from Etsy/Shopify order exports using only paid sales and the agreed commission rate.
5. Keep listing and commission outputs traceable to supplied product/sales records and do not invent prices or missing terms.
6. Keep `PROOF.md` clear that fixture data is synthetic and no live shop action was performed.
7. Exercise commission imports with synthetic fixtures using Etsy's seller Orders CSV field names and Shopify's documented order-export headers, including Shopify's blank continuation rows for multi-item orders. Cite Etsy's export instructions (which do not publish the complete header row) and Shopify's documented CSV schema in the acceptance test.
8. Calculate the commission from the signed agreement's stated eligible amount and explicit handling of discounts, shipping, sales tax, platform fees, refunds, partial refunds, returns, and chargebacks. Exclude/reverse/refund-adjust orders exactly as the written rule says; if the relevant term or input data is missing or unsupported, report the result as uncertain and do not claim an amount due.
9. Use currency-safe decimal arithmetic and the agreement's stated rounding rule, rounding the final commission to the currency's minor unit.
10. Reject or clearly report uncertainty for mixed or unsupported currencies; never combine unlike currency amounts into one commission total.
11. The commission flow only prepares a local calculation/report. It never sends an invoice or message, charges a payment method, or transfers money automatically; any payment requires a separate owner action.
