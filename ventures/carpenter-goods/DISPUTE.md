# Dispute — legacy commission acceptance fixtures

The signed-terms safety rule makes five existing checks fail because their
fixtures expect a payable amount from an unsigned rate or incomplete terms.
These checks are under `tests/acceptance` and were left unchanged because they
are independently owned acceptance coverage.

## `tests/acceptance/test_commission_flow.py`

- `test_platform_export_fixtures_have_real_headers_and_paid_orders_are_counted_once`
  supplies no rate-file terms but expects two eligible sales and a commission.
  Give the synthetic orders complete terms with `signed: true`, an explicit
  eligible amount basis, shipping and tax rules, fee and refund rules, rate,
  and rounding rule; keep its count-once and amount assertions.
- `test_agreement_terms_control_refunds_fees_shipping_tax_discounts_and_partial_refunds`
  includes an unsigned, incomplete term set. Add `signed: true` and the explicit
  rounding rule to its otherwise valid item-subtotal/refund terms; retain the
  `$220.00` eligible basis check.
- `test_refunded_or_canceled_orders_do_not_create_commission` supplies no
  signed terms and asserts a zero payable amount. Either provide complete
  signed terms and retain the zero-due assertion for fully excluded orders, or
  assert an uncertain result with `commission_due is None` when specifically
  testing the no-terms case.
- `test_commission_rounding_uses_decimal_currency_rules` supplies only a rate
  and rounding rule. Add complete signed terms and an explicit eligible basis;
  retain the half-up `$0.01` assertion.

## `tests/acceptance/test_v_carpenter2.py`

- `test_commission_calculator_uses_paid_sales_and_explicit_rate` passes an
  explicit rate without signed terms and expects `$20.00` payable. Make the
  synthetic sale include the agreed eligible amount fields, pass a complete
  signed terms object, and retain the paid-only `$20.00` result assertion.

The independent signed-terms tester in
`tests/acceptance/test_C-CARPENTER-COMMISSION-TESTER.py` already checks that
missing, unsigned, or incomplete terms cannot produce a payable amount; it was
not changed. This dispute records the exact legacy fixture corrections needed
for the whole acceptance directory to pass without relaxing that safety rule.
