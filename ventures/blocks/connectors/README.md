# Platform connectors

Read-only Python clients for Jobber GraphQL, ShipStation REST v2, Shopify Admin GraphQL, and Apify REST v2. The package uses Glacier's OS keychain store at request time; tokens are never placed in files, URLs, exceptions, or command output. Each client only exposes read operations. GraphQL mutations and REST writes are refused. Pagination is bounded, and 429/5xx/network failures use at most three attempts with `Retry-After` honored up to 30 seconds.

The app ID, app secret, account sign-in, identity checks, OAuth consent, and marketplace submissions are owner steps. Do not paste credentials into source files or shell arguments. In Glacier, open **Settings → Secrets**, add each named secret below, and paste its value there. The secret names are labels; only values are kept in the operating-system keychain.

## Owner setup and connection checks

Run these commands from the repository root after saving the credentials in Glacier. Each command performs a harmless read and prints only a short connection result.

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors jobber
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors shipstation
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors shopify --shop YOUR-STORE.myshopify.com
~/w/glacier-lean/.venv/bin/python -m ventures.blocks.connectors apify
```

### Jobber

1. **Start early:** sign in to the [Jobber Developer Center](https://developer.getjobber.com/), open **My Apps**, and create an app for Glacier. Jobber requests an app review after it connects to more than five paying accounts.
2. In the app configuration, set the app name and support/contact details. Configure a real HTTPS OAuth callback and manage-app URL when the Glacier OAuth callback is deployed; do not invent a callback URL. Request only the read permission for completed jobs needed by the connected venture.
3. Copy the Client ID and Client Secret from the app details into Glacier Secrets as `jobber_client_id` and `jobber_client_secret`.
4. In Developer Center's GraphiQL sandbox, connect the owner's Jobber test account and save its OAuth Access Token and Refresh Token in Glacier Secrets as `jobber_access_token` and `jobber_refresh_token`. Jobber access tokens expire after about 60 minutes. The client refreshes on HTTP 401 and saves rotated tokens back to the OS keychain.
5. Run the Jobber command above. Expected output: `{"account":"…","connected":true}`.

### ShipStation

1. Sign in to the owner's ShipStation test account and open **Settings → API Settings**.
2. Generate a v2 API key. ShipStation displays it once; copy it directly into Glacier Secrets as `shipstation_api_key`.
3. Run the ShipStation command above. It reads one shipment page only. Expected output includes `"connected":true`.

### Shopify

1. Open the [Shopify Dev Dashboard](https://dev.shopify.com/dashboard/), choose **Apps → Create app → Start from Dev Dashboard**, and create the connector app.
2. Open the app's **Versions** page. Add only the `read_products` access scope for the current FDA cosmetics read workflow, then release the version.
3. Install the app on a development store in the same Shopify organization. Under **Settings → Credentials**, copy Client ID and Client Secret into Glacier Secrets as `shopify_client_id` and `shopify_client_secret`.
4. Run the Shopify command below. For an app and store in the same organization, the client exchanges those credentials for the 24-hour Admin API access token and saves it in Glacier's keychain. After expiry, a 401 causes a fresh exchange. For a store outside the owner's organization, the merchant must authorize the distributed app through OAuth; save the resulting Admin API token in Glacier Secrets as `shopify_admin_access_token`.
5. Run the Shopify command above with the store's exact `*.myshopify.com` domain. Expected output includes `"connected":true` and the store domain.

### Apify

1. **Start early:** create/sign in to the owner's [Apify Console](https://console.apify.com/), complete the owner's payout setup, then open **Settings → API & Integrations** and create a dedicated token named `Glacier read-only connector`.
2. Limit the token to the read permissions needed for the account check and selected datasets. Do not grant actor run, create, or modify access to this client.
3. Copy the token into Glacier Secrets as `apify_api_token`.
4. Run the Apify command above. Expected output includes `"connected":true` and the account username.

## Marketplace listing and review text (owner submits)

These drafts are ready to paste into the platform listing forms. The owner must review, complete contact and URL fields, provide the screenshots/logo, and submit. Listing approval and the first public publish are owner-only steps.

### Jobber App Marketplace

**Name:** Glacier Warranty Registration<br>
**Short description:** Keep completed HVAC installs organized for warranty registration.<br>
**Description:** Glacier reads completed installation jobs from Jobber so a contractor can prepare manufacturer warranty registrations and track their registration deadlines. The contractor reviews each record and authorizes any registration, homeowner email, or other action before it is sent. Glacier requests read-only job access and does not change Jobber jobs.<br>
**Data and permissions:** Read completed jobs and the minimum customer/job fields needed to identify an installation. No write access.<br>
**Reviewer steps:** Connect a Jobber test account; confirm that completed jobs appear in Glacier; verify that a new job is not edited or messaged; disconnect the app and confirm access stops.<br>
**Privacy summary:** Job data is used only for the connected contractor's selected workflow, stored on the contractor-controlled Glacier machine, and not used for advertising. Job data is removed when the contractor disconnects or deletes the job under Glacier's retention settings.

**Submission checklist:** Enable Developer Center two-factor authentication; verify callback and manage-app URLs; upload a square PNG/SVG logo at least 384 × 384 pixels and below 1 MB; add gallery screenshots; complete features and benefits, support, privacy, and data handling fields; confirm only necessary read scopes; test connect, read, disconnect, and error states; submit for review only after the owner has five eligible test accounts, as required by the venture queue.

### ShipStation app listing / partner review

**Name:** Glacier Freight Claim Packet<br>
**Short description:** Organize shipment records for customer-reviewed freight claims.<br>
**Description:** Glacier reads shipment and tracking records from ShipStation to identify possible loss or damage events and prepare a claim packet for the shipper to review. Glacier does not buy labels, create shipments, change orders, or submit claims without the shipper's explicit approval.<br>
**Data and permissions:** Read shipment identifiers, shipment status, dates, and carrier/tracking details needed for the selected claim. No write operations.<br>
**Reviewer steps:** Connect a ShipStation test account; confirm shipment pages are read-only; verify pagination and throttling behavior; confirm no shipment, label, rate, or claim is created or changed; revoke the key and confirm reads fail.<br>
**Privacy summary:** Shipment records are used only to prepare the shipper's requested claim packet, remain on the shipper-controlled Glacier machine, and are removed after the job retention period.

**Submission checklist:** Complete ShipStation partner/API application; provide privacy policy, support contact, redirect/callback details if required, product screenshots, and a test-account walkthrough; document requested shipment fields and least-privilege controls; test a sandbox/test account, key revocation, 401 and 429 handling; submit after owner review. Confirm ShipStation's current app listing and partner requirements in the portal before submission.

### Shopify App Store

**Name:** Glacier Cosmetics Listing Prep<br>
**Short description:** Prepare a reviewable cosmetics product list from Shopify catalog data.<br>
**Description:** Glacier reads product titles, handles, vendors, and product types from Shopify so a cosmetics brand can prepare its FDA listing checklist. The brand confirms every product and ingredient before any regulatory file is prepared or submitted. Glacier never submits FDA filings and never changes Shopify products.<br>
**Data and permissions:** `read_products` only for the first release. No customer data, checkout data, inventory changes, or product write permissions.<br>
**Reviewer steps:** Install on a development store; confirm products load and paginate; compare displayed products with Shopify Admin; verify no product mutations or FDA submissions occur; uninstall and confirm token access ends.<br>
**Privacy summary:** Catalog data is processed for the store owner's requested listing-preparation workflow, kept on their Glacier machine, and not sold or used for advertising.

**Submission checklist:** Create the app through Shopify's required app build/distribution path; complete app URL, support, privacy, and data-use fields; request only `read_products`; add icon, screenshots, and reviewer instructions; verify install, OAuth, pagination, rate-limit recovery, uninstall, and data deletion; complete Shopify's current review and protected-data declarations; owner submits the listing.

### Apify Store actor listing

**Name:** Contractor License Status Lookup — [State]<br>
**Short description:** Check a public state-board license record and return its status, expiry date, and source link.<br>
**Description:** This actor checks the named public state licensing board for the supplied license number or contractor name. It returns the status and expiry date with the source URL, or `unverifiable` when the official page cannot be read. It skips login-only and CAPTCHA-protected sources and applies a per-run request limit.<br>
**Inputs:** `licenseNumber` (string, optional) or `name` (string, optional); provide at least one.<br>
**Output fields:** `status`, `expiryDate`, `sourceUrl`, `checkedAt`, and `result` (`match` or `uncertain — please check`).<br>
**Reviewer steps:** Run the three published canary licenses; compare status and expiry with the linked state-board pages; run a malformed lookup; confirm it returns `unverifiable`; inspect rate limits and verify the actor does not access login/CAPTCHA pages.<br>
**Privacy summary:** The actor reads only the stated public licensing board and returns the source URL with each result. Input is not used for advertising or sold.

**Submission checklist:** Complete the actor name, owner, category, pricing, input schema, output schema, README, sample input/output, source and terms disclosure, support contact, and version notes; record three canary license numbers whose public lookup terms permit automated access; include rate-limit behavior and an `unverifiable` result example; have a separate reviewer test the actor and listing; owner approves and publishes the first three actors.

## Operating notes

- Every client is read-only and bounded to 100 pages by default; pass a smaller `max_pages` for tighter jobs.
- `get_jobs`, `get_shipments`, `get_products`, and `get_dataset_items` return raw records from the official API. They do not decide legal status or file anything.
- Do not use this block to scrape a logged-in consumer platform, bypass CAPTCHA, or call an undocumented endpoint.
- Retry behavior is bounded (three total tries). Pagination stops on the API's page metadata or a short/empty page. Connector errors intentionally omit response bodies and credential values.
