# Shopify App Review testing instructions

**Test store:** `glacier-test-cosmetics` (owner should confirm exact `.myshopify.com` URL and allow Shopify review access.)

**Credentials:** The app has no separate Glacier login. Shopify Admin installs and authenticates the app. Do not provide a real store owner's password or API token to reviewers.

1. Install Glacier FDA Listing in the review store through Shopify's review flow. Grant only the displayed `read_products` permission.
2. Open the app from Shopify Admin. Confirm the catalog shows the test product as uncertain and shows its Shopify catalog source.
3. Confirm no product, order, or customer records are changed. No Shopify write scope is requested.
4. To test a charge, select Starter or Studio and approve the Shopify test subscription. The plan uses a 14-day trial. Shopify handles approval and billing. Use the app's plan form to test a plan change; the Billing API replacement behavior is `STANDARD`.
5. To prepare a packet, enter the synthetic fixture's brand details and upload the matching test label. A successful packet is a draft SPL ZIP. If any detail or label reading is uncertain, the app must show the confirmation list and must not produce a ZIP.
6. Verify that the draft shows the 120-day and annual review dates when corresponding dates were supplied.
7. Verify that the app never signs or submits to FDA. The responsible person handles any FDA Cosmetics Direct submission.
8. Send the three Shopify compliance webhooks to `/webhooks/compliance`. Valid requests receive HTTP 200. Shopify webhook HMAC verification rejects invalid signatures. `shop/redact` removes that shop's session rows; catalog and uploaded label files are not retained.

The accompanying screencast and screenshots use the checked-in synthetic development-store fixture only. They do not demonstrate a real FDA filing, acceptance, or customer product.
