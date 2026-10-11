# CPSC data prep

CPSC data prep turns importer certificates and lab reports into a CPSC Product
Registry CSV draft, a source-linked gap list, and a per-importer batch status
board. It does not certify or submit anything. The importer or the importer's
licensed customs broker reviews every field, certifies it, and submits through
their own authorized CPSC route.

The broker product is a white-label importer portal with a flat monthly fee.
Direct customers choose a $19, $29, or $49 batch checkout plan. Broker pricing
is intentionally unset until the owner selects a flat monthly amount. Checkout
links use Stripe test mode until the owner provides a live key. No percentage or
refund-based broker fee is offered.

For the batch flow, place the customer's `batch.json` and its source documents
under `$GLACIER_HOME/ventures/cpsc-prep/incoming/`. Drafts and results are
written under that venture's `drafts/` and `results/` folders, where the owner
can review them across the approval wait.

Customer-facing results use only `match`, `no match found in [sources] as of
[date]`, or `uncertain — please check`. The checker refreshes the flagged
tariff-code list, CPSC rule-code list, and registry template from the
government-feed block. It preserves source pages, leaves absent values blank,
reports each gap, and will not release a CSV when the independent extraction
disagrees, a tariff/rule code is unknown, or the customer has not certified.
Missing required fields stay blank, appear in the gap list, and also block CSV
release.
Every public code page identifies its source and says it is an independent
service, not a government notice.

## Shared block functions used

- `ventures.blocks.reader.read_document(path, schema=None)`
- `ventures.blocks.rules.check(fields, ruleset)`
- `ventures.blocks.feeds.sync(source_id)`
- `ventures.blocks.feeds.query(source_id, **filters)`
- `ventures.blocks.customer.create_customer(...)`
- `ventures.blocks.customer.checkout_link(plan)`
- `ventures.blocks.customer.status_page(customer_id)`
- `ventures.blocks.customer.support_inbox()`
- `ventures.blocks.mail.landing_pages(objects, template)`

The venture assumes these feed IDs: `cpsc_flagged_tariff_codes`,
`cpsc_rule_codes`, and `cpsc_registry_template`. The feeds block must map them
to current official data and return template columns as `{"columns": [...]}`;
the template may also provide `field_map` when its column names differ from the
reader's stable field names.
The fixed reader contract has no second-engine method. The CLI uses a separately
configured local Ollama model (`GLACIER_OLLAMA_URL` and `GLACIER_LOCAL_MODEL`)
for re-extraction; without it, cross-check results stay uncertain and no CSV
can be released. Unit tests inject a fake second engine and fakes for blocks
that have not merged yet.

## Your steps

1. Before any broker contract or launch, attach and confirm the trade lawyer's
   written opinion on the flat-fee broker model.
2. For each batch, review all extracted fields beside their cited source pages,
   resolve uncertainties, and certify as importer or licensed broker.
3. Review and sign the first broker contract yourself; confirm it is flat-fee
   only with no refund commission or attorney fee split.

No real accounts are created or contacted by this venture. CPSC submission,
customer signatures, and live payment setup remain with the customer/owner.
