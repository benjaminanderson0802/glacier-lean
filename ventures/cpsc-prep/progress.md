# CPSC data prep progress

Card V-CPSC advances PH12.9. PH12 depends on PH5 and PH9, both at exit; this
venture is assigned as parallel-safe in wave 6. It serves P-CONTROL and
P-USABLE, with M-VERIFIED and M-INTERVENE, by requiring review and certification
before release, with source pages and independent extraction agreement for
every field.

Implemented: CPSC batch preparation, source-linked field and gap review,
customer certification gate, exact-template CSV generation, per-importer status
board, test-mode checkout adapter, daily source refresh, code-page preparation,
manifest, four Glacier flows, broker portal product, $19/$29/$49 direct batch
plans, and the trade-lawyer opinion approval wait. A follow-up guard now blocks
CSV release when any required certificate field is blank.

Block functions relied on: `reader.read_document`, `rules.check`,
`feeds.sync`, `feeds.query`, `customer.create_customer`,
`customer.checkout_link`, `customer.status_page`, `customer.support_inbox`,
and `mail.landing_pages`. Their fixed contract is in
`ventures/blocks/CONTRACT.md`; tests use fakes because the block packages are
still being built in parallel.

Release is not yet verified: real feed/reader/rules/customer/mail checks and a
successful end-to-end CPSC batch in Glacier await those blocks, a configured
local second engine, and the spec's public data/sandbox checks. The earlier live
Glacier attempt registered all four flows and confirmed the broker launch flow
waited at the lawyer approval; the batch command stopped because those shared
blocks were not yet present. No checkpoint status was changed.
