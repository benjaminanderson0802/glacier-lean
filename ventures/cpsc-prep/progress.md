# CPSC data prep progress

Card V-CPSC advances PH12.9. PH5 and PH9 remain in progress; this venture is
assigned as parallel-safe in wave 6 and may start without marking its checkpoint
complete. It serves P-CONTROL and
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
`ventures/blocks/CONTRACT.md`; isolated tests use block fakes and do not verify
the shared blocks' live sources or release checks.

Release is not yet verified: the integrated installer validates all four flows,
but the feed registry lacks the required CPSC list/template IDs and the current
venture fields do not satisfy the merged `cpsc_efiling.json` ruleset. Missing
source IDs now produce an uncertain result. The public feed/reader/rules checks,
configured local second engine, and successful end-to-end batch are still
required. The earlier broker launch flow waited at the lawyer approval; the
batch command failure due to absent shared blocks is historical and those blocks
are now present. The latest isolated suite passes 18 tests; no checkpoint status
was changed.
