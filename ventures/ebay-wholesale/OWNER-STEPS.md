# eBay wholesale: three owner setup steps

Glacier prepares the local listing and unsent PO drafts. You submit the account forms and supplier applications below; do not create accounts or submit listings through this document. These setup actions are one-time. Estimated times assume your legal/contact details and bank details are at hand; eBay or suppliers may request more documents.

## 1. Verify the eBay seller account and payouts — about 10–20 minutes

Open [eBay Seller Center](https://www.ebay.com/sellercenter) → `Start selling` → sign in to the account you will use, or register yourself if needed → complete seller identity/business verification with your actual information → in Seller Hub open `Payments` → `Payout settings` → add the matching business checking account or eligible debit card → finish eBay's verification prompts. Stop if the account asks for documentation you do not have; provide documents only in eBay's signed-in flow. Confirm the seller and payout status shows verified.

**Enter:** account/business identity exactly as on the actual legal and bank records. Do not use an assumed EIN, address, or account type.

## 2. Create eBay developer keys — about 15–25 minutes

Open [eBay Developer Program – Application Keys](https://developer.ebay.com/my/keys) → sign in or select `Join` and complete registration → create a `Sandbox` keyset for test work → create a `Production` keyset when ready → complete any eBay account-deletion/closure-notification compliance prompt → use eBay's OAuth flow to authorize only the Sell Inventory and Fulfillment scopes this tool needs. Save the OAuth user token in Glacier Settings → `Secrets` as `ebay_user_access_token`; never paste credentials into the CSV, flow, or repository. eBay production access to restricted APIs is separately controlled; a developer key does not provide Marketplace Insights access.

**Enter:** application name `Anderson Education eBay Wholesale`; environment `Sandbox` for test keyset; production keyset only when ready to use real Seller APIs. Keep the issued keys/tokens private.

## 3. Submit the prefilled supplier applications — one sitting, about 25–35 minutes

Open the prepared [supplier application packet](research/SUPPLIER-APPLICATIONS.md) and apply in this order: Mammoth Attachments → Medal Equipment → Wholesale By Travers. Each section has exact links, clicks, known values to paste, and an inquiry text. Fill only the `OWNER: enter/confirm` fields from current records; never guess. Check every required field and the written text, then personally submit each web form/email. No phone calls are needed. An inquiry is not supplier approval; do not list any supplier SKU until the supplier confirms in writing that its terms authorize eBay resale and direct-to-buyer shipping for that SKU.

**Georgia ST-5, when needed for qualifying tax-free wholesale purchases:** check the [Georgia DOR dealer/registration guidance](https://dor.georgia.gov/tax-registration). If registration applies and is not already active, personally register Sales & Use Tax through [Georgia Tax Center](https://dor.georgia.gov/how-register-sales-and-use-tax-account). Mammoth asks whether a resale/sales-tax permit is on file for tax-free purchases; answer `No` unless the actual permit is issued. After a valid Georgia sales-tax registration number exists, open the DOR's [Form ST-5](https://dor.georgia.gov/document/form/st-5-sales-tax-certificate-exemption/download), complete a separate copy with the actual supplier name/address and your true purchaser, registration, business, and signature details, and give it to a supplier only for purchases that qualify for resale exemption. The DOR says a properly completed ST-5 is the Georgia certificate for resale purchases and requires a valid sales-tax registration number on the certificate. If tax-free buying is not needed or registration does not apply, do not file or provide ST-5 merely because a form exists. This is a conditional legal/tax step; check with Georgia DOR or your tax professional if applicability is unclear.

## After setup

Before real drafts, add only supplier-approved products, actual landed cost, current fees, accurate inventory and dispatch lead time, permitted images, and the supplier's actual ship-from location key. The eBay sold-data research pack is ready for the orchestrator, but its execution remains gated on eBay's express permission or another documented eBay-approved access basis. Apify is the authorized runner, not permission from eBay. No eBay API write, publication, supplier order, or payment is part of account setup; each still needs its own owner approval.
