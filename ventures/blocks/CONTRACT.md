# Shared building block interfaces

These public call shapes are fixed. A block owner may add functions but must preserve these signatures.

```python
# reader
read_document(path, schema=None) -> {"fields": {name: {"value", "page", "confidence", "uncertain"}}, "text"}

# rules
check(fields, ruleset) -> {"verdict": "pass"|"fail"|"uncertain", "results": [{"rule", "verdict", "cite", "detail"}]}

# feeds
sync(source_id) -> {"rows", "changed", "alerts"}
query(source_id, **filters) -> list[dict]

# deadlines
add(item_id, start_date, rule, label)
due(on_date) -> list[dict]

# filer
prepare(portal_id, fields, auth) -> draft
submit(draft, approval_id) -> confirmation

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
