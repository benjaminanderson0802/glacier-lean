# C-CARPENTER-COMMISSION-TESTER evidence

## Drift check

- **Checkpoint:** PH12.20 (Carpenter's goods). PH5 and PH9 remain in progress; the owner-authorized PH12 card allows this work to start, but this does not authorize marking PH12.20 done.
- **Properties and metrics:** P-VERIFY / P-CONTROL; M-VERIFIED / M-AUDIT.
- **Existing tools:** The venture already has CSV readers, Decimal arithmetic, and pytest. This card adds only independent synthetic acceptance cases; it adds no billing integration or implementation.
- **Acceptance first:** Only explicitly supplied signed and complete terms may produce a deterministic amount. Missing or unsigned terms, missing required inputs, conflicting amount columns, or unsupported/mixed currency must leave the result uncertain with no amount due and no payment action.

## Frozen cases

`ventures/carpenter-goods/tests/acceptance/test_C-CARPENTER-COMMISSION-TESTER.py` contains synthetic cases for:

- an item subtotal after discounts, excluding shipping, tax, and excluded fees;
- signed status and completeness of commission terms, including required refund treatment;
- conflicting order-total columns;
- partial and full refunds;
- mixed USD/EUR and unsupported EUR currency;
- final half-up rounding to the currency minor unit and local-only report status.

The Etsy Orders CSV field-name fixture follows the documented seller export instructions, which do not publish its complete header row. The Shopify fixture follows the documented order-export CSV schema. Fixture rows contain no customer information and are not merchant exports.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods/tests/acceptance/test_C-CARPENTER-COMMISSION-TESTER.py` — **11 passed, 4 failed**. Full output: `independent-acceptance.log`.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods/tests` — **31 passed, 4 failed**. Full output: `venture-suite.log`.

Four active failures identify behavior the independent cases require the calculator to fix:

1. A rate-only terms file produces a payable commission without signed agreement evidence.
2. Complete-looking but explicitly unsigned terms produce a payable commission.
3. Omitting the refund rule from the supplied terms still produces a payable commission.
4. Conflicting `Order Total` and `Total` columns are silently resolved by precedence despite an explicitly signed order-total basis.

Passing new cases confirm the discounted item basis, shipping/tax exclusion, partial refund reduction, full-refund exclusion, decimal rounding, mixed/unsupported currency uncertainty, and local-only report. The existing commission code and existing acceptance checks were not edited. PH12.20 remains unverified; no checkpoint status was changed.

## Anti-pattern review

The new file contains executable black-box CSV acceptance cases based on the venture requirements; it is not a narrative-only substitute for implementation. No existing judging check was changed. No evidence here claims a live merchant export or a signed maker agreement.
