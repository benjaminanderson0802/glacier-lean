# Customer block release evidence

Checkpoint: PH12.6 (customer layer). The final repository acceptance suite was run against recorded/local test data.

Command:

```sh
$HOME/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests
```

Output:

```text
..........                                                               [100%]
10 passed in 12.27s
```

Compilation check:

```sh
$HOME/w/glacier-lean/.venv/bin/python -m compileall -q ventures/blocks/customer
```

Result: exit 0, no output.

The acceptance tests cover local account persistence, explicit missing Stripe-secret guidance, rejection of a live Stripe key, a completed recorded checkout purchase and approved refund, an HTTP-served local signature page producing a hash-linked PDF and JSON audit record, escaped static status HTML, read-only IMAP retrieval, and support replies held as drafts until approved.

The Stripe key-presence check returned `false` without displaying a value. Running the documented live-check command with a test price produced:

```text
Stripe is not configured. Add STRIPE_SECRET_KEY in Glacier Settings > Secrets.
```

No request was made to Stripe. A real Glacier venture flow is not part of this block card and is not installed in this worktree yet; PH12.1-3 are not complete in this branch snapshot. No screenshot was produced because the block has no Glacier UI screen. PH12.6 is not marked done here because the separate evaluator required by the Venture Build Spec has not reviewed this result.
