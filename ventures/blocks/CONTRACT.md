# Shared venture block contracts

Python packages are imported as `ventures.blocks.<block>`. A block owner may add
functions, but these signatures and return shapes stay fixed.

```python
reader.read_document(path, schema=None) -> {
    "fields": {name: {"value", "page", "confidence", "uncertain"}}, "text": str
}
rules.check(fields, ruleset) -> {
    "verdict": "pass" | "fail" | "uncertain",
    "results": [{"rule", "verdict", "cite", "detail"}]
}
feeds.sync(source_id) -> {"rows": list, "changed": bool, "alerts": list}
feeds.query(source_id, **filters) -> list[dict]
deadlines.add(item_id, start_date, rule, label)
deadlines.due(on_date) -> list[dict]
filer.prepare(portal_id, fields, auth) -> draft  # filled form and screenshot; never submits
filer.submit(draft, approval_id) -> confirmation  # idempotent; saves PDF/screenshot
customer.create_customer(...)
customer.checkout_link(plan)
customer.request_signature(doc_path, signer)
customer.status_page(customer_id)
customer.support_inbox()
mail.verify_address(...)
mail.postcard(front_html, back_html, to, from_)
mail.landing_pages(objects, template) -> site_dir
connectors.jobber(...)
connectors.shipstation(...)
connectors.shopify(...)
connectors.apify(...)
```

Rulesets live under `ventures/blocks/rules/rulesets/`. Feed IDs live in
`ventures/blocks/feeds/sources.json`; the feed database is a rebuildable index
under `$GLACIER_HOME/ventures/feeds.db`. Customer integrations stay in Stripe
test mode until the owner configures a live key. E-sign must be free/open-source.
Mail uses a test key until the owner configures live delivery.
