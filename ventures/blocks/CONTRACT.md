# Shared building block contract

These public call shapes are fixed. A block owner may add functions but must preserve
these signatures. Blocks are importable as `ventures.blocks.<block>`.

```python
# ventures.blocks.reader
read_document(path, schema=None) -> {
    "fields": {
        "<name>": {
            "value": <value>,
            "page": <1-based page number or null>,
            "confidence": <0.0..1.0>,
            "uncertain": <bool>
        }
    },
    "text": <extracted text>
}

# ventures.blocks.rules
check(fields, ruleset) -> {
    "verdict": "pass" | "fail" | "uncertain",
    "results": [
        {"rule": <rule id>, "verdict": "pass" | "fail" | "uncertain",
         "cite": <official source>, "detail": <plain explanation>}
    ]
}

# ventures.blocks.feeds
sync(source_id) -> {"rows": <records>, "changed": <bool>, "alerts": <list>}
query(source_id, **filters) -> list[dict]

# ventures.blocks.deadlines
add(item_id, start_date, rule, label)
due(on_date) -> list[dict]

# ventures.blocks.filer
prepare(portal_id, fields, auth) -> draft  # filled form + screenshot; never submits
submit(draft, approval_id) -> confirmation  # idempotent; saves PDF/screenshot

# ventures.blocks.customer
create_customer(details) -> account
checkout_link(plan) -> URL
request_signature(doc_path, signer) -> signature request
status_page(customer_id) -> local static HTML path
support_inbox() -> messages

# ventures.blocks.mail
verify_address(address) -> verification result
postcard(front_html, back_html, to, from_)
landing_pages(objects, template) -> site dir

# ventures.blocks.connectors
jobber(**kwargs)
shipstation(**kwargs)
shopify(**kwargs)
apify(**kwargs)
```

Rulesets are JSON or YAML files under `ventures/blocks/rules/rulesets/`.
Reader and rules outputs are preparation aids: they do not certify, legally
determine, sign, or submit government filings. Missing or conflicting evidence
must remain visible for the customer to confirm.

Feed IDs live in `ventures/blocks/feeds/sources.json`; the feed database is a
rebuildable index under `$GLACIER_HOME/ventures/feeds.db`. Customer integrations
stay in Stripe test mode until the owner configures a live key. E-sign must be
free/open-source. Mail uses a test key until the owner configures live delivery.
