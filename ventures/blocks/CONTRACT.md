# Shared building block contract

The signatures below are fixed. A block owner may add functions without changing
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
create_customer(...)
checkout_link(plan)
request_signature(doc_path, signer)
status_page(customer_id)
support_inbox()

# ventures.blocks.mail
verify_address(...)
postcard(front_html, back_html, to, from_)
landing_pages(objects, template) -> site_dir

# ventures.blocks.connectors
jobber(...), shipstation(...), shopify(...), apify(...)
```

Rulesets are JSON or YAML files under `ventures/blocks/rules/rulesets/`.
Reader and rules outputs are preparation aids: they do not certify, legally
determine, sign, or submit government filings. Missing or conflicting evidence
must remain visible for the customer to confirm.
