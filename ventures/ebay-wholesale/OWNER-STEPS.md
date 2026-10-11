# Owner setup step: eBay seller, developer, and supplier accounts

This is the one-time setup step. Use a browser and do these actions yourself; Glacier does not create accounts, submit applications, or accept terms.

## eBay seller account and payouts

1. Open [eBay Seller Center](https://www.ebay.com/sellercenter) and select **Start selling**. Sign in to the eBay account you will use for this business, or choose **Register** and complete the account form yourself.
2. Follow the seller registration screens. Choose the account type that matches your real legal/business status; do not create a business identity or enter a tax ID that is not yours.
3. In the seller setup or any **Action needed** banner, complete identity and business verification requested by eBay.
4. Open Seller Hub → **Payments** → **Payout settings**. Add the checking account or eligible debit card whose owner/name matches your eBay account, then complete eBay's verification prompts.
5. Confirm Seller Hub shows the seller account and payout method as verified. eBay may request additional documents; provide them only through eBay's signed-in site.

## eBay developer keys

6. Open [eBay Developer Program – Application Keys](https://developer.ebay.com/my/keys) and sign in with your developer account. If you do not have one, use **Join** and finish registration yourself.
7. Under **Sandbox**, select **Create a keyset**. Enter a descriptive application title and create the sandbox keyset. Keep this keyset for fixture/sandbox work.
8. Request a **Production** keyset only when you are ready to use the tool. Complete eBay's account-deletion/closure notification compliance step if the page shows it; production access to restricted APIs can require additional eBay approval.
9. Create the user authorization/token for Sell Inventory and Fulfillment scopes through eBay's OAuth flow after the application keyset is active. Save the user token in Glacier Settings → **Secrets** as `ebay_user_access_token`. Never put keys or tokens in CSVs, JSON files, or this repository.
10. Ask each approved supplier in writing for the physical warehouse address that will dispatch your orders. In the Developer Program, open **API Explorer** → choose **Production** → **Sell** → **Inventory** → **createInventoryLocation**. Enter a unique `merchantLocationKey`, the supplier's confirmed actual `postalCode` and `country`, a location name, `merchantLocationStatus: ENABLED`, and `locationTypes: [WAREHOUSE]`; review and submit this account write yourself. Repeat for each distinct supplier ship-from address. Never guess or substitute your own address if the supplier ships elsewhere. Record each returned location key in that supplier's catalog rows.
11. In Seller Hub, record your current payment, fulfillment, and return policy IDs. For each supplier lead time, choose or configure a fulfillment policy with handling time no shorter than the supplier's confirmed dispatch lead. Use only supplier lead times you can consistently meet. Marketplace Insights sold-data access is restricted; do not assume a new keyset grants access.

## Wholesale supplier applications

12. Apply online to the suppliers in [research/suppliers-and-niches.md](research/suppliers-and-niches.md), starting with Mammoth Attachments, Travers Tool, and Medal Equipment. Use each supplier's dealer/distributor application, enter truthful business details, select eBay where the form asks about sales channels, and submit through the supplier site yourself.
13. Ask each supplier in writing (email or its own contact form) to confirm: reseller approval for eBay, blind/direct-to-buyer shipping, supplier stock and dispatch lead times, real landed freight by destination, returns/warranty responsibility, image/catalog reuse, MAP or price rules, inventory feed format, account minimums, and whether a resale certificate or EIN is required. Do not place an opening order or accept paid terms without your separate approval.
14. Keep the written approval and terms locally. Add only approved supplier products and their confirmed costs, inventory, lead times, registered ship-from location key, licensed photos, and category-specific eBay item specifics to the incoming catalog. The calculator will reject missing essentials; review each output and approve every API write, publish action, supplier PO, and payment separately.

The supplier's published requirements differ. For example, Mammoth's dealer application says a resale/sales-tax permit is required for tax-free resale buying; other listed suppliers do not publish a definitive EIN/resale-certificate rule on the cited page, so ask them in writing. No phone calls are part of this step.
