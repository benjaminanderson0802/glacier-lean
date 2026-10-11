# Customer block

This local Python package stores customer accounts and workflow records in SQLite beneath `$GLACIER_HOME/ventures/` (or `./data/ventures/`). Database, generated signature, and status-page files use owner-only permissions where the operating system supports them. `STRIPE_SECRET_KEY` and IMAP password values are resolved by Glacier's OS keyring secret store; they are never read from environment variables or written to the database.

## Billing

`checkout_link(plan, approval_id=None)` creates a Stripe Checkout Session using only an `sk_test_` key. Set a test price as `STRIPE_PRICE_<PLAN>` or pass a plan map to the function. In test mode, the approval ID may be omitted; when supplied, it is included in Stripe metadata and the local audit event. The returned HTTPS link is for the customer to open. This block refuses live Stripe keys, so a missing approval can never enable a live session. Refunds require a non-empty owner approval ID, include it in Stripe metadata, and store an audit event locally.

Run the owner-driven live test with one command after saving an `sk_test_` key as `STRIPE_SECRET_KEY` in Glacier Settings > Secrets and preparing a Stripe test price:

```sh
STRIPE_TEST_PRICE_ID=price_... $HOME/w/glacier-lean/.venv/bin/python -m ventures.blocks.customer.live_stripe_check
```

The command creates a test Checkout Session and displays the link. Complete checkout with `4242 4242 4242 4242`, then paste the test PaymentIntent ID and an owner approval ID when prompted to request a test refund. To stop before refund, leave the PaymentIntent prompt blank. Without a test key, it exits with the Settings > Secrets instruction. No account signup, live transaction, or key entry is performed by the block.

## E-signature

`request_signature(doc_path, signer)` creates a local signature page and records the source document's SHA-256. Glacier (or a local signature-page host bound to loopback) presents that page to the named signer. `sign_document(...)` requires an explicit consent checkbox and an exact name match, refuses if the source file changed, and creates a compact signed certificate PDF plus a JSON audit record that contains the original and output hashes, signer, consent, and UTC timestamp. The source is identified by hash rather than embedded into the certificate; retain the original beside the certificate. The PDF uses a small standard-library writer so no new PDF dependency is bundled.

To host pending pages on the same computer, run:

```sh
$HOME/w/glacier-lean/.venv/bin/python -m ventures.blocks.customer.signature_server
```

The server binds only to `127.0.0.1`. A venture flow should hand the signer the URL returned by `request_signature`; exposing it to another device requires the owner to publish it through their own approved secure host.

## Support inbox and customer status

`support_inbox()` connects to IMAP over implicit TLS and opens the mailbox read-only. It stores the newest 100 fetched messages locally. `draft_reply()` stores a reply as `pending_approval`; `send_reply()` refuses unless an approval ID and an SMTP sender are supplied, then records the approval in the audit log. Status pages are escaped, static HTML files written locally. Copy/publishing them is an explicit owner action.

For IMAP setup, save the password in Glacier Settings > Secrets (for example as `SUPPORT_IMAP_PASSWORD`), then call `configure_support_inbox({"host": "imap.example.com", "username": "support@example.com", "mailbox": "INBOX", "password_secret": "SUPPORT_IMAP_PASSWORD"})`. Only connection metadata and the secret's name are saved; the password is resolved from Glacier's keyring at read time.

No support replies, pages, or customer messages are sent or published automatically.
