# Product Recall Checker (CPSC, NHTSA, FDA)

**Title:** Product Recall Checker (CPSC, NHTSA, FDA)

**Short description:** Check a barcode, brand, model, or product name against public CPSC, NHTSA, and FDA recall records.

**Description:** Enter one item or a batch of up to 100. Each result shows `match`, `no_match`, or `uncertain — please check`, with the sources checked, UTC check time, and links to matching official records. Exact barcode/UPC matches are checked first, followed by strict brand-and-model matching. A source outage never becomes a clean no-match. Verify important results with the official source; this tool is an information aid and does not decide whether a product is safe or legal to sell.

**Inputs:** One object with `barcode`, `brand`, `model`, `product_name`, and optional vehicle `year`, or a `queries` array of up to 100 such objects. NHTSA vehicle checks need make, model, and year.

**Output:** One item per query with outcome, explanatory message, source records, source status and check times. A no-match message lists only sources successfully checked.

**Official public sources:** CPSC SaferProducts.gov Recalls API; NHTSA vehicle recalls API; FDA openFDA food, drug, and device enforcement APIs. No account key is required by this Actor. FSIS is not included in this version.

**Pricing:** Pay per event: **$0.01 per completed query**. Results caused only by source outages are not charged. A partial result is charged when at least one source responds. Platform usage is included. Configure a maximum run charge and disable Apify's automatic `apify-default-dataset-item` charge event before publication.

**Important:** Recall data can be incomplete, delayed, or changed. Verify an important result directly with the relevant official source. Do not treat a no-match as proof that a product is safe.

**Your steps:** Deploy the Actor, configure its event and maximum charge in Apify Console, and review the listing before publishing.
