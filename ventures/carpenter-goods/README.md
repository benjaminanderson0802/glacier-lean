# Carpenter's goods

This venture prepares product drafts for the carpenter's Etsy shop and Shopify site, then calculates the agreed commission from paid sales exported by the owner. It does not sign up for platform accounts, contact buyers, publish listings, or move money.

To prepare a listing, put `product.json` and `comparables.json` in `$GLACIER_HOME/ventures/carpenter-goods/incoming/`, then run **Prepare a handmade furniture listing** in Glacier. Product facts and local photo paths must come from the maker. Comparable rows must be completed sales in the same category and include a source URL and sale price. With fewer than three eligible rows the price is left blank and the result is **uncertain — please check**. The script only uses source-linked owner-supplied rows; it does not scrape Etsy.

The result is a private local JSON draft for Etsy and Shopify. Check every fact, price and photo, then publish by hand after the owner approves the first listing. Photo paths are carried through for review; photo edits and uploads are manual. Outputs are written with owner-only permissions where supported. Keep uploads on the local machine and remove them within 30 days after a job closes unless the customer asks to keep them.

To track commission, put the owner's paid order export in `incoming/paid-sales.json` and a `commission-terms.json` file with the agreed `rate` (a decimal from 0 to 1) in the same folder, then run **Track agreed furniture commissions**. Enter the rate only after agreeing it in writing. The report is only a calculation; compare it with the written agreement and platform settlement before invoicing or transferring anything.

No shared block is imported: the spec does not assign a block to Carpenter's goods, and the available connectors cannot read Etsy completed sales or publish Etsy/Shopify listings. The Shopify connector is read-only and does not fit this flow. No block was changed. Existing block docs reviewed: customer, mail, connectors and filer; reader, rules, feeds and deadlines packages are absent from this base branch.

## Your steps

1. Agree the commission rate in writing with the carpenter.
2. Supply product facts, photos, at least three source-linked completed-sale comparisons, and paid order exports.
3. Review and approve the first listing, then publish it manually in Etsy and Shopify.

## Checks

Run the focused tests and manifest validation listed in [PROOF.md](PROOF.md). The test comparisons are synthetic fixtures, not market data. A real pricing run needs current sale records supplied by the owner.
