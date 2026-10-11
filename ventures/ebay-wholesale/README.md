# eBay wholesale drop-ship listings

This venture prepares eBay listing request drafts from a catalog supplied by an approved wholesale supplier, then prepares an unsent supplier PO draft from an eBay order. It targets high-priced commercial equipment and specialized parts. The seller remains responsible for on-time delivery and buyer satisfaction.

eBay permits direct fulfillment by a wholesale supplier, but does not allow listing an item and then buying it from another retailer or marketplace for direct shipment to the buyer. See the current [eBay drop-shipping policy](https://www.ebay.com/help/policies/selling-policies/drop-shipping-policy?id=4176). The [eBay User Agreement](https://www.ebay.com/help/policies/member-behavior-policies/user-agreement?id=4259) restricts automated access without prior express permission; the [Marketplace Insights API](https://developer.ebay.com/api-docs/buy/marketplace-insights/static/overview.html) is limited-release. No marketplace data has been collected. The exact 14-query Apify pack is prepared for the orchestrator in [APIFY-QUERIES.md](research/APIFY-QUERIES.md) and [JSON inputs](research/apify-sold-listings-queries.json); it must not run until an eBay permission reference or another documented, eBay-approved access basis is on file. Apify is the selected runner, not permission from eBay.

## What is built

* `listings`: parses a supplier CSV and generates local request bodies/paths for the official Sell Inventory API (`PUT inventory_item`, then `POST offer`). It calculates a minimum break-even price from owner-entered actual supplier and fee inputs and chooses the smallest currently allowed eBay handling time that is no shorter than the supplier's stated business-day dispatch lead.
* `po`: parses an owner-exported or official Sell Fulfillment API `GET order` payload and makes a local, unsent supplier PO draft. The owner reviews ship-by date, buyer address, SKU mapping, cost, stock, freight, promised dispatch, and returns before any PO is sent.
* `EbaySellApi`: an official eBay REST adapter for order reads, inventory locations/items, offers, and publish API calls. It defaults to sandbox. Each write method requires explicit owner approval and a durable audit-event writer before it can make a network call; publishing has its own approval argument. This task did not call the adapter against eBay or publish anything.

The tool does not log in through a browser, create accounts, write supplier portals, forward POs, place purchases, pay, or publish. It does not automate any eBay research/scraping. API drafts can still be incomplete until category item specifics, ship-from location, current handling-time metadata, payment/fulfillment/return policy IDs, freight and the supplier's written eBay resale permission are entered and checked. The adapter's audit-writer hook is an interface only; this task does not connect it to Glacier's durable event log. Therefore live API writes remain disabled until that audited runtime integration is supplied and verified.

## Input files

Copy the [catalog template](templates/supplier-catalog.csv) to `$GLACIER_HOME/ventures/ebay-wholesale/incoming/supplier-catalog.csv`. One row is one supplier-backed SKU. Fill `unit_cost` and `shipping_cost` with confirmed values; shipping must include every known seller-paid supplier/freight charge. `supplier_lead_days` means business days until the supplier hands the shipment to the carrier. Set `aspects_json` using the exact eBay category metadata for that item. Use only supplier-licensed HTTPS images. Condition must be the exact supported eBay enum in this tool.

Copy [pricing rules](templates/pricing-rules.example.json) to `incoming/pricing-rules.json` and enter current fee rates verified by the owner from the applicable eBay category/seller fee schedule. `minimum_profit_usd` defaults conceptually to zero because owner rules say to minimize profit while maximizing accepted offers; the CSV tool still requires the value to be explicit. This is a break-even floor, not an earnings estimate. Include any seller-paid outbound freight, category surcharges, ad fees, or other variable cost in the input before setting a price. The formula cannot make missing costs safe.

Put the owner's actual eBay `fulfillmentPolicyId` per handling time in `incoming/fulfillment-policy-ids.json`, keyed like `EBAY_US|5`. These are existing seller-account policies; the venture does not create one. Inventory API location keys must refer to eBay inventory locations at the real supplier ship-from address. The owner creates each location through the official API after obtaining that address from the supplier (see [OWNER-STEPS.md](OWNER-STEPS.md)); add its returned key to the CSV's `merchant_location_key` column. The flow's command-line location key is only a fallback and placeholder; do not use it as a real key.

Prepare local listing drafts from the repository root:

```sh
~/w/glacier-lean/.venv/bin/python ventures/ebay-wholesale/scripts/ebay_wholesale.py listings \
  --catalog "$GLACIER_HOME/ventures/ebay-wholesale/incoming/supplier-catalog.csv" \
  --rules "$GLACIER_HOME/ventures/ebay-wholesale/incoming/pricing-rules.json" \
  --policies "$GLACIER_HOME/ventures/ebay-wholesale/incoming/fulfillment-policy-ids.json" \
  --location-key YOUR_SELLER_LOCATION_KEY \
  --allowed-handling-days 0,1,2,3,4,5,10,15,20 \
  --output "$GLACIER_HOME/ventures/ebay-wholesale/drafts/listing-payloads.json"
```

The allowed handling-time values above are a starter list from eBay documentation and can change by marketplace. Verify current values through eBay's official metadata before use. The script rounds up to a supported value so the listed handling time is never shorter than supplier lead time; it stops when no supplied value is long enough. eBay describes handling time as payment receipt to carrier scan, and the seller must meet the displayed delivery promise. For long freight items, configure a policy and shipping service that reflect actual freight transit as well.

## Order forwarding

The [Fulfillment API fixture](tests/fixtures/fulfillment-order.json) is shaped like an official `getOrder` response. Use the read-only API adapter or export order JSON, map every eBay SKU to the verified wholesale supplier in a local `supplier-map.json`, and prepare a PO draft:

```sh
~/w/glacier-lean/.venv/bin/python ventures/ebay-wholesale/scripts/ebay_wholesale.py po \
  --order "$GLACIER_HOME/ventures/ebay-wholesale/incoming/fulfillment-order.json" \
  --supplier-map "$GLACIER_HOME/ventures/ebay-wholesale/incoming/supplier-map.json" \
  --output "$GLACIER_HOME/ventures/ebay-wholesale/drafts/supplier-po.json"
```

This output contains buyer delivery details and must remain local and restricted. It is always marked `DRAFT_FOR_OWNER_APPROVAL`; it is not an order request and is never sent. Owner reviews the current eBay ship-by date against supplier availability and freight before approving a purchase. Supplier purchase/payment and eBay shipment/tracking updates are separate owner-approved actions.

## Research and limits

The niche and supplier memo ranks five segments. It reports public supplier price anchors, not eBay realized prices; sold volume, sell-through, exact competition counts, wholesale pricing, and net margins remain uncertain. The exact application packet ([SUPPLIER-APPLICATIONS.md](research/SUPPLIER-APPLICATIONS.md)) lists public program evidence, prefilled truthful values, and the written questions still needed for account approval. Supplier pages identify potential programs, not existing business relationships. Confirm by written application/approval that a supplier allows eBay resale, direct shipment to eBay buyers, use of supplied images/data, agreed lead time, returns, warranty, MAP rules, and account documents before using its catalog. Georgia [Form ST-5](https://dor.georgia.gov/document/form/st-5-sales-tax-certificate-exemption/download) is only for qualifying resale purchases and requires an actual valid Georgia sales-tax registration number; see the [DOR resale guidance](https://dor.georgia.gov/taxes/business-taxes/sales-use-tax/nontaxable-sales). No account has been created and no application submitted.


## Owner steps

Complete the three grouped setup steps in [OWNER-STEPS.md](OWNER-STEPS.md): verify eBay seller/payouts, create developer credentials, and submit the prepared supplier applications. Per-item API writes, each publish action, each supplier PO, and each payment still require separate owner review and approval at run time.
