# Independent acceptance findings — fba-fee-check

The acceptance checks are independent of the TSV comparator and its existing
tests. Run date: 2026-10-10. Amazon's official Settlement Reports reference and the distinction
between source fields and the seller's local fee schedule are in
[ACCEPTANCE.md](ACCEPTANCE.md). The single live canary returned HTTP 200 from
the official Amazon settlement report documentation and found
`quantity-purchased`; it did not access seller data or SP-API. Output is in
[`tests/acceptance/evidence/live-canary.log`](tests/acceptance/evidence/live-canary.log).

Offline run: `~/w/glacier-lean/.venv/bin/python -m pytest -q -k 'not live_official_document_contract' tests/acceptance` — **5 failed, 14 passed, 1 deselected**. Failures are left in place:

- Sale amounts are aggregated by settlement/order/SKU without shipment or
  order-item key, producing incorrect per-unit margins for split shipments.
- Missing expected fees and missing or negative quantities use internal
  `uncertain_*` flags but not the required customer-facing `uncertain - please
  check` vocabulary.
- Decimal `NaN` reaches comparison and raises `decimal.InvalidOperation`, not a
  controlled validation error.

Prospect review: all 14 entries link an Amazon-owned seller story/directory as
the provenance source and a business-controlled website/contact route; no
person-specific email or phone is provided. Several seller/FBA relationships
are explicitly “unconfirmed” or only reported in an Amazon story, and no row
proves current FBA use, fee-review need or purchase intent. Some routes are
general home pages rather than a dedicated contact form; owner should identify
the correct business channel before any manual approach. All contacts remain
untouched. The kit uses seller-supplied files, and its flow has no account
login, fee dispute, sending, publishing, payment or automatic charge action.
