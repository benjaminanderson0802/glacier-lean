# Customer layer release check

Run the recorded-response end-to-end tests:

```sh
$HOME/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests
```

They cover SQLite account persistence, clear missing-secret guidance, rejection of live Stripe keys, a completed recorded checkout purchase followed by an approval-tagged refund, a served signature page that creates a signed PDF and linked audit JSON, static HTML escaping, IMAP read-only retrieval, and support replies that stay pending until owner approval and are audited after send.

Owner live check when `STRIPE_SECRET_KEY` is saved in Glacier's keyring as a Stripe **test** key and a test price exists:

```sh
STRIPE_TEST_PRICE_ID=price_... $HOME/w/glacier-lean/.venv/bin/python -m ventures.blocks.customer.live_stripe_check
```

This one command creates a test Checkout Session and prints its link. Complete checkout with Stripe's test card `4242 4242 4242 4242`, paste the test PaymentIntent ID, then enter an owner approval ID to authorize the test refund. Leave the PaymentIntent prompt blank to stop before refund. If the test key is absent, the command prints the Glacier Settings > Secrets instructions and exits without a Stripe request.
