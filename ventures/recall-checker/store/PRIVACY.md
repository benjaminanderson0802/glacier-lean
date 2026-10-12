# Glacier Recall Checker privacy policy

**Developer:** Glacier (Benjamin Anderson)  
**Applies to:** Glacier Recall Checker Chrome extension, version 0.1.0

Glacier Recall Checker handles page content and product details only to provide a recall lookup.

When you click **read this page**, the extension checks that the current tab URL uses HTTP or HTTPS and reads the tab's title and visible text (up to 12,000 characters) in your browser to suggest a product name, barcode, brand and model. The URL check is local and the URL is not saved or sent. It does not read tabs in the background, crawl sites, retain the page text, or send page text to the lookup service.

The selected check mode and optional Apify Actor ID are saved in `chrome.storage.local` on your device. The optional Apify API token is held only in the open popup. It is sent to Apify in the HTTPS authorization header only when you select hosted mode and run a check; it is not saved after the popup closes. Product details entered or extracted for a lookup are not saved by the extension after the popup closes.

In local mode, the item details you submit are sent to Glacier's API at `http://127.0.0.1:8765` on your own computer. In hosted mode, which you must choose and configure, the item details are sent to Apify's Actor API over HTTPS and your API token is sent in the HTTPS authorization header. Apify is the only third party configured by the extension. Apify's handling of requests is governed by Apify's terms and privacy policy. The extension does not send item details to Glacier's servers, use analytics or advertising, or sell data.

To remove saved hosted settings, clear the Actor ID and change the field so the empty value is saved, or remove the extension. The API token is not saved between popup sessions. This policy describes this extension's behavior; it does not describe Glacier's separate local API or other services.

We may update this policy when extension data practices change. The version date will be updated with a policy change.

## Chrome Web Store Limited Use statement

Glacier Recall Checker uses information accessed through its permissions only to provide the recall lookup features described in the extension and its Chrome Web Store listing. It does not sell user data, use it for personalized advertising or creditworthiness, or transfer it for unrelated purposes. Hosted-mode transfer to Apify occurs only when the user selects hosted mode and runs a check. Humans do not read user data except with the user's specific consent, as necessary for security, or as required by law.
