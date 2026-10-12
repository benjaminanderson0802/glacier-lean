# fba-fee-check acceptance

Parse actual Settlement V2 TSV columns and seller-provided fee expectations.
Preserve source row/order/item/shipment references; calculate quantity-aware dollar
variance and per-unit margins using the matching item/shipment sale, not other
shipments. Handle settlement summary rows and blank non-applicable cells. Refuse
non-finite/ambiguous numbers, missing columns and unsupported currencies. Missing
expectations or quantities are uncertain. No refund promise, dispute, account access
or charge. Source outage/429 upstream means no usable file and no billable digest.

## Independent tester plan / drift check

Owner Benjamin approved T-PILOTS on 2026-10-10. This advances PH12.22,
P-VERIFY and P-CONTROL, and M-FALSE-DONE, M-VERIFIED and M-AUDIT.
PH5/PH9 remain in_progress; assigned-card authorization permits this audit,
not a phase completion claim. Use existing pytest and Python standard-library
fixtures; no new service or dependency. These criteria precede new tests.
The tester did not build the product and will not change it or its existing tests.

## Shared acceptance rules

- Synthetic values must use documented source fields, types and envelopes.
  Customer mapping fields must be identified as local, never called official API fields.
- Empty input is distinct from missing, malformed, unavailable, rate-limited or
  incomplete input. Such uncertainty must not become a confident negative.
- Customer-visible uncertain results use `uncertain — please check` (an ASCII
  hyphen is also accepted). Valid negative results name the source and date.
- Source-outage-only results never cause a charge. Manual pilot invoices require
  owner action and the kit's buyer acceptance gates. No test sends, publishes,
  registers, pays, or uses a live charging SDK.
- Preserve Unicode names and identifiers. Do not infer absent facts.
- Audit every prospects row for official provenance and business-only contact
  routes. Reachability alone is not proof of a current contact or buyer fit.
- `RUN_LIVE=1` enables read-only public-document/contact canaries. Account-data
  canaries require already configured credentials; skips must say why. No
  automated Alabama notice/license extraction. Public-doc checks do not prove
  authenticated production delivery. Live failures remain failures, never xfail.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q tests/acceptance` from
this kit; prefix `RUN_LIVE=1` for canaries. Evidence and limitations are recorded
in `TEST-FINDINGS.md` and `tests/acceptance/evidence/`.

## Source field provenance

The TSV fixture follows Amazon's official Flat File V2 Settlement Report
attribute list: `settlement-id`, `settlement-start-date`, `settlement-end-date`,
`deposit-date`, `total-amount`, `currency`, `transaction-type`, `order-id`,
`merchant-order-id`, `adjustment-id`, `shipment-id`, `marketplace-name`,
`amount-type`, `amount-description`, `amount`, `fulfillment-id`, `posted-date`,
`posted-date-time`, `order-item-code`, `merchant-order-item-id`,
`merchant-adjustment-item-id`, `sku`, `quantity-purchased`, and `promotion-id`.
Amazon documents this as tab-delimited and explains that `amount-type`,
`amount-description`, and `amount` carry price/fee values in local currency in
the [Settlement Reports reference](https://developer-docs.amazon.com/sp-api/docs/report-type-values-settlement).
The separate `sku`, `size_tier`, `expected_fee_usd_per_unit`, and
`unit_cost_usd` CSV is a seller-provided local mapping, not an Amazon schema.
This kit intentionally accepts only USD and does not fetch settlement data.
