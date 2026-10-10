# Shared building block contract

These public call shapes are fixed. A block owner may add functions but must preserve these signatures. Blocks are importable as `ventures.blocks.<block>`.

```python
# reader
read_document(path, schema=None) -> {"fields": {name: {"value", "page", "confidence", "uncertain"}}, "text"}

# rules
check(fields, ruleset) -> {"verdict": "pass"|"fail"|"uncertain", "results": [{"rule", "verdict", "cite", "detail"}]}

# feeds
sync(source_id) -> {"rows": "records", "changed": bool, "alerts": list}
query(source_id, **filters) -> list[dict]

# deadlines
add(item_id, start_date, rule, label)
due(on_date) -> list[dict]

# filer
prepare(portal_id, fields, auth) -> draft  # filled form + screenshot; never submits
submit(draft, approval_id) -> confirmation  # idempotent; saves PDF/screenshot

# customer
create_customer(details) -> account
checkout_link(plan) -> URL
request_signature(doc_path, signer) -> signature request
status_page(customer_id) -> local static HTML path
support_inbox() -> messages

# mail
verify_address(address) -> verification result
postcard(front_html, back_html, to, from_)
landing_pages(objects, template) -> site dir

# connectors
jobber(**kwargs)
shipstation(**kwargs)
shopify(**kwargs)
apify(**kwargs)
```

Rulesets are JSON or YAML files under `ventures/blocks/rules/rulesets/`.
Reader and rules outputs are preparation aids: they do not certify, legally determine, sign, or submit government filings. Missing or conflicting evidence must remain visible for the customer to confirm.
