# Chrome Web Store listing — Glacier Recall Checker

Paste the values below into the matching Chrome Web Store dashboard fields. The package is version 0.1.0. Suggested URLs become usable after this change is available on the public repository's default branch.

## Store listing

**Name**  
Glacier Recall Checker

**Summary (74/132 characters)**  
Check an item against public recall data from the product page you choose.

**Detailed description**  
Check an item you are viewing against recall records from CPSC, NHTSA, FDA and FSIS.

Choose **read this page** to extract a product name, barcode, brand or model from the current tab. Review the fields, add a vehicle model year if needed, and choose **check item**. The extension reads a page only after you click the button; it does not crawl websites or scan tabs in the background.

By default, item details are sent to Glacier's local recall API at 127.0.0.1 on your computer. You can optionally choose hosted Apify Actor mode and enter your own Actor ID and API token. Hosted checks send the item fields to Apify over HTTPS. Your mode and Actor ID are saved in this browser's extension storage. The API token stays only in the open popup and is not saved after it closes. Page text is read in the browser to find item details and is not sent as page text.

Results link to official notices when a match is found. A no-match result means no match was found in the available sources as of the displayed date; it is not a guarantee that an item has never been recalled. Missing or stale source data and borderline matches are reported as uncertain. Verify the linked official notice before making a decision.

**Category**  
Shopping

**Language**  
English (United States)

**Single-purpose statement**  
Glacier Recall Checker helps a user check a product they choose against public product recall records by extracting or entering item details and sending those details to the user's selected local or hosted recall checker.

## Permission justifications

**activeTab**  
Allows the user-initiated “read this page” action to access the currently active tab after the user opens the popup and clicks the button. The extension does not read tabs in the background or crawl pages.

**scripting**  
Runs a small, packaged function in the current tab after the user clicks “read this page” to read the page title and visible body text, limited to 12,000 characters, so the popup can suggest item details. No remote script is loaded or executed.

**storage**  
Uses `chrome.storage.local` to save the selected check mode and optional Apify Actor ID between popup openings. The optional API token stays in the open popup only and is not saved. Product fields entered for a check are not saved by the extension.

**http://127.0.0.1:8765/* (host permission)**  
Allows the extension to POST user-submitted item fields to Glacier's local recall API on the same computer when local mode is selected. This is a loopback-only HTTP endpoint; no page content or browser history is sent there.

**https://api.apify.com/* (host permission)**  
Allows the extension to POST user-submitted item fields to the Apify Actor run endpoint over HTTPS when the user selects hosted mode. It is used only after the user has provided an Actor ID and token and chosen hosted mode.

## Remote code

**Does the extension use remote code?**  
No. All executable extension code is included in the submitted package. The extension sends item data to the selected API and renders returned data; it does not download or execute code.

## Privacy practices dashboard answers

Use these disclosures to match the packaged code and the popup's existing disclosure. Dashboard wording can change; use the closest matching choices and keep these explanations in the developer notes.

**User data handled**  
Select **Website content**: after a button click, page title and visible text are read locally in the browser to suggest product details. Select **Web browsing activity** if the dashboard category includes current-tab URLs: the active tab URL is checked locally only to allow HTTP/HTTPS pages; it is not retained or transmitted. Select **Authentication information**: the optional Apify API token is entered in the popup and sent as a bearer credential to Apify only for hosted checks; the extension does not save it between popup sessions. Select **Other** if available, and describe it as product identifiers/details (barcode, brand, model, year and product name) supplied or confirmed by the user. Do not claim that the extension collects browsing history, location, personal communications, health data, or financial data.

**Collection and use**  
The extension reads the current page only after an explicit click. It checks the current tab URL locally only to confirm it is an HTTP or HTTPS page, and does not retain that URL or the page text. It uses the item details to request a recall lookup. Item details are sent to the loopback service in local mode, or to Apify only in user-selected hosted mode. Settings are saved locally in Chrome extension storage. There is no analytics, advertising, tracking, account registration, or sale of data implemented in the extension.

**Third-party sharing**  
Apify receives the item details and the user-provided API token as an HTTPS authorization header only when hosted mode is selected and a check is run. In local mode, item details go to the local loopback API and are not sent by the extension to Apify. Chrome's storage service stores the selected mode and optional Actor ID on the user's device; the extension does not use Chrome Sync and does not save the API token. No other third party is configured by the extension. Apify's own handling and retention are governed by Apify's terms and privacy practices.

**Limited Use certifications**  
Certify only if the owner confirms these statements remain accurate at submission: user data is used only to provide the recall lookup; it is not sold or transferred for advertising, creditworthiness, or unrelated purposes; it is not used for personalized advertising; and humans do not read user data except with specific user consent or where required for security or law. Apify is the user-selected service provider for hosted checks, which is a transfer necessary to provide that requested feature. The extension does not currently send item data to the developer.

**Privacy policy URL**  
https://github.com/benjaminanderson0802/glacier-lean/blob/main/ventures/recall-checker/store/PRIVACY.md

## Public URLs

**Homepage suggestion**  
https://github.com/benjaminanderson0802/glacier-lean/blob/main/ventures/recall-checker/store/PRIVACY.md

This page also contains the required Limited Use statement. The repository root is a better general project homepage only after it links to this policy from its README.

**Support URL suggestion**  
https://github.com/benjaminanderson0802/glacier-lean/issues

The repository's issue tracker must be enabled and monitored before using it as the support URL. The links above assume the owner merges this card to the public repository's default branch. A 128x128 store icon is included as `store-icon-128.png`. Current dashboard documentation also lists a promotional video link among listing assets; no public video URL is supplied in this card, so leave that field blank if the dashboard permits, or have the owner provide a video URL before submission. This extension package and its listing assets have not been uploaded or submitted.

## Store artwork

- `screenshots/01-local-check.png` — 1280 × 800 PNG
- `screenshots/02-hosted-mode.png` — 1280 × 800 PNG
- `screenshots/03-small-promo-tile.png` — 440 × 280 PNG
- `store-icon-128.png` — 128 × 128 PNG

No headless Chromium or Playwright renderer was installed. The HTML mockups in `mockups/` use inline SVG and were rasterized by the available CairoSVG tool. They are illustrative interface mockups, not browser captures.

## Manifest and policy review

The manifest is MV3, declares only `activeTab`, `scripting`, `storage`, and two specific API hosts, and contains no background worker, content-script match patterns, or broad all-sites host access. Code review confirms no remotely hosted executable code. These declarations are narrowly connected to the current-tab read and selected local/hosted lookup behavior. Chrome's current policy says permissions must be the narrowest needed and MV3 code must be bundled. [Chrome Web Store permissions policy](https://developer.chrome.com/docs/webstore/program-policies/permissions), [Manifest V3 remote hosted code guidance](https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code).

Chrome requires accurate privacy disclosures and Limited Use handling. The optional hosted-mode token is not saved between popup sessions and is sent only in the user-selected hosted request. The owner should confirm the dashboard's current disclosure choices match this behavior when submitting. [Chrome Web Store user data policy](https://developer.chrome.com/docs/webstore/program-policies/policies).
