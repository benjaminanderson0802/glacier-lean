# CPSC data prep

CPSC data prep turns importer certificates and lab reports into a CPSC Product
Registry CSV draft, a source-linked gap list, and a per-importer batch status
board. It does not certify or submit anything. The legally responsible and
authorized certifier reviews each field and certifies it; an importer or broker
acts only in the role allowed for that product. The authorized filer submits
through their own CPSC route.

**Ready for owner review; not live.** The official source refresh and code-page
preview have run through Glacier using live CPSC data. The batch flow has run
through Glacier with a synthetic certificate and a local second model; it
stopped for human review and did not release a CSV. See [PROOF.md](PROOF.md)
for run IDs and the exact limits of that evidence.

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

Live checks on 2026-10-10 retrieved the CPSC HTS flagging workbook, citation
and testing-exception workbook, and version 3 Product Registry upload template
from the official [eFiling Document Library](https://www.cpsc.gov/eFiling-Document-Library).
The feed block also retrieved CPSC's public [Recalls REST API](https://www.saferproducts.gov/RestWebServices/)
from SaferProducts.gov; that recalls feed is separate from certificate data
preparation. All four live feed canaries returned records without alerts, and
an immediate second sync reported no changes. These source checks do not prove
that a customer's certificate is complete, compliant, or ready to file. The
HTS flagging list is a screening aid, not a complete applicability decision.

The former HTTP 403 note referred to earlier fetch attempts and is no longer a
current description of the CPSC feeds. The current check and command results
are recorded in `PROOF.md`; the broader source-block evidence is in
[`ventures/blocks/feeds/CHECK.md`](../blocks/feeds/CHECK.md).

The fixed reader contract has no second-engine method. The CLI uses a separately
configured local Ollama model (`GLACIER_OLLAMA_URL` and `GLACIER_LOCAL_MODEL`)
for re-extraction; without it, cross-check results stay uncertain and no CSV
can be released. Unit tests inject a fake second engine and fakes for blocks
for fixture inputs; the ruleset adapter is also checked with the real rules
checker. Those tests do not substitute for a real customer batch.

Before any paid launch, broker contract, or broker-portal onboarding, the owner
must obtain the trade lawyer's written opinion on the exact proposed service
and fee model, including both the flat monthly broker fee and direct batch
plans.
Use [LAWYER-QUESTIONS.md](LAWYER-QUESTIONS.md) as the counsel checklist. The
opinion remains a hard launch gate; the document is not legal advice or a
substitute for the lawyer's written conclusion.

The lawyer-question checklist cites the governing statutes, regulations, and
CPSC guidance. The `trade-lawyer-opinion` launch gate remains in
`venture.json`; no paid launch or broker onboarding is enabled by the checklist
or its automated checks.

## Your steps

1. Before launch, get a trade lawyer's written opinion on the exact service
   and fees; choose the broker price, configure any live account or payment
   credential, and sign any broker contract yourself. For each real batch,
   review its fields and sources, certify only if legally authorized, and have
   the authorized filer submit it. Review and approve the saved preview before
   publishing any optional public code pages; confirm any broker contract is
   flat-fee only, with no refund commission or attorney-fee split.

These are owner actions. In particular, Glacier does not create accounts, make
payments, certify, file with CPSC/CBP, sign contracts, or publish the optional
public code pages. The lawyer opinion gates paid launch for either customer
channel; the first contract is required to onboard a broker. Certification is
required for each batch that the owner releases for filing.

No real accounts are created or contacted by this venture. CPSC submission,
customer signatures, and live payment setup remain with the customer/owner.
