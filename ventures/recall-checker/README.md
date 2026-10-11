# Recall checker

Recall checker checks a product against public recall records from CPSC, NHTSA, FDA and FSIS. It can check an item you choose in Chrome, process a store inventory CSV, answer a local JSON API request, and generate source-linked local recall pages. A result is **match**, **no match found in CPSC, NHTSA, FDA and FSIS as of [date]**, or **uncertain — please check**. Missing, stale or incomplete feeds and borderline matches stay uncertain.

The extension reads the current tab only after you click **read this page**. It never crawls a marketplace. By default, it extracts a barcode, brand, model and product name in the browser and sends only those fields to the local API on `127.0.0.1`; page text is not sent or saved. Add a model year for vehicle checks. The optional hosted mode sends item fields to the Apify Actor you configure. Its Actor ID, token, and selected mode are saved in `chrome.storage.local`. Start the local API from the repository root with:

```sh
~/w/glacier-lean/.venv/bin/python ventures/recall-checker/scripts/api.py
```

Refresh feeds and generate local HTML pages with **Refresh recall data and pages**. Pages are stored under `$GLACIER_HOME/ventures/recall-checker/pages/`. The first-page review flow requires a current, alert-free snapshot for every source before it asks for review, and creates only 50 pages for the owner review packet. It will not produce an incomplete set that could be mistaken for complete coverage. The prepared packet from current public data is in [evidence/first-50-pages](evidence/first-50-pages/).

For a store, place `inventory.csv` in `$GLACIER_HOME/ventures/recall-checker/incoming/` and run **Check a store inventory file**. The output is a separate flagged CSV in `outputs/`; the original is unchanged. API clients can send `POST /api/match` with JSON such as `{"item":{"barcode":"012345678905","brand":"Example","model":"BL-100"}}`. The API listens on loopback only at `http://127.0.0.1:8765`.

## Source status

The documented [FSIS Recall API](https://www.fsis.usda.gov/science-data/developer-resources/recall-api) returns JSON from `https://www.fsis.usda.gov/fsis/api/recall/v/1`. The live canary requests it with the same transparent `Glacier public-data client` User-Agent and ordinary JSON Accept header used by the shared feed adapter. It returned HTTP 200 and 2,030 records, all with recognized recall identifiers. An earlier canary used a longer client User-Agent, which returned 403; matching the actual adapter's client identity corrected that request without browser impersonation or access bypass. The official [FSIS recalls RSS](https://www.fsis.usda.gov/RSS/usdarss.xml) also returned HTTP 200 with 10 recent notices. The [HHS/CDC combined food-safety RSS](https://www2c.cdc.gov/podcasts/createrss.asp?c=146) returned HTTP 200 but had no FSIS-linked records among the 20 sampled items. The results are recorded in [the canary artifact](evidence/fsis-official-source-canary.json); tests include successful API parsing, partial RSS handling, and the all-sources-unavailable case.

The [Data.gov FSIS annual recall summaries dataset](https://catalog.data.gov/dataset/fsis-summary-of-recall-cases-in-calendar-year) describes yearly summaries and links to FSIS pages; the catalog reports its dataset update as May 8, 2023. It is not used as a substitute for the current record-level FSIS API. The RSS is a recent-notice fallback only; it never establishes complete source coverage by itself.

The [FSIS canary](scripts/fsis_canary.py) exits `0` only when the documented FSIS JSON endpoint returns records with the expected identifier canary. It reports RSS-only records as partial and does not mark the source complete. If no official endpoint returns verifiable FSIS records, it exits `2` and reports the coverage gap. It uses normal HTTP requests with a transparent client identifier; it does not impersonate a browser or bypass access restrictions.

## Plans

The free tier covers single lookups. `plans.json` records owner-approved ranges for individual and store plans, plus an API plan that needs an owner-selected price. Checkout is not active until test prices and a Stripe test key are configured in Glacier Secrets. The shared customer block refuses live Stripe keys. No live billing is configured.

## Matching limits

Exact barcode/model matches are automatic. For NHTSA vehicle records, make, model and model year must agree with the structured recall row; narrative-only model overlap stays **uncertain — please check**. Borderline results are not decided by an unverified second model.

The committed 500-recalled/500-clean benchmark passes on the NHTSA vehicle slice: 0 false negatives, 0 false-positive matches, 100% precision and recall. Of 500 clean cases, 261 returned no-match and 239 remained uncertain for review. This is a source-coverage benchmark, not an individual-VIN or cross-source accuracy claim; see [benchmark methods and limits](bench/README.md). The independent local-model/second-engine review for fuzzy matches remains open in `claim-ph12-12-recall-benchmark-engine`.

## Chrome extension package

The local listing package is prepared in `store/`: use [STORE-LISTING.md](store/STORE-LISTING.md) for text and privacy-dashboard disclosures, [PRIVACY.md](store/PRIVACY.md) for the public privacy policy, and `recall-checker-extension-0.1.0.zip` for upload. The PNG screenshots and icon were generated locally from the included mockups with:

```sh
~/w/glacier-lean/.venv/bin/python ventures/recall-checker/store/render_mockups.py
~/w/glacier-lean/.venv/bin/python ventures/recall-checker/store/build_extension.py
```

The screenshots are illustrative mockups, not browser captures. Load `extension/` using `chrome://extensions` → **Developer mode** → **Load unpacked** to review the actual popup. Privacy text describes the current behavior, including that the optional Apify token is stored in extension local storage. The owner should verify the final Chrome Web Store privacy disclosures before submission.

## Current status and owner actions

The source canary passes for the official FSIS API and the real CLI generated the first 50 pages from current snapshots of all four sources. The independent fuzzy-match release review is still open, so the venture is not yet ready for public launch. The live run evidence and remaining technical gate are in [PROOF.md](PROOF.md). The Web Store account is registered and the Recall Actor is deployed; neither account setup nor package preparation verifies public operation.

The only remaining human actions after the non-owner data and verification gates pass are listed with exact clicks, copy-ready values and time estimates in [OWNER-STEPS.md](OWNER-STEPS.md). They are review/host selection and marketplace publication/price choices. No phone calls or cold outreach are planned.
