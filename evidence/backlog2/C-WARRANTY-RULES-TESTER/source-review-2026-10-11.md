# C-WARRANTY-RULES-TESTER source review

Reviewed 2026-10-11 against official manufacturer pages. The acceptance cases
are offline and use synthetic unit/job details. They test policy dates without
treating those dates as proof of a unit's warranty coverage or registration
eligibility.

## Frozen source facts

| Brand case | Synthetic installation/model input | Official source and supported policy | Expected calculated date |
| --- | --- | --- | --- |
| Carrier | 2026-01-01; unreadable model and serial | [Carrier warranty information](https://www.carrier.com/us/en/residential/homeowner-resources/warranty/): eligible new residential equipment in Consumer Choice must be registered within 90 days; eligible products and regional limitations apply. | 2026-04-01 |
| Trane | 2026-01-01; unreadable model and serial | [Trane warranty and registration](https://www.trane.com/residential/en/resources/warranty-and-registration/): a Registered Limited Warranty requires registration within 60 days; product terms and state/province exclusions vary. | 2026-03-02 |
| Goodman | 2026-01-01; unreadable model and serial | [Goodman HVAC Learning Center](https://www.goodmanmfg.com/resources/hvac-learning-center): qualified purchases can receive enhanced coverage with registration within 60 days; warranty duration and registration requirements vary by state/province. | 2026-03-02 |
| Amana | 2026-01-01; unreadable model and serial | [Amana Standard Warranty](https://www.amana-hac.com/support/standard-warranty): stated enhanced coverage requires registration within 60 days; the exact unit certificate still controls. | 2026-03-02 |
| Lennox | 2026-01-01; unreadable model and serial; Texas | [Lennox product registration](https://www.lennox.com/residential/owners/register-and-review/product-registration/index): eligible equipment outside named exceptions requires registration within 60 calendar days. | 2026-03-02 |
| Daikin DX4SQ | 2026-01-01; model DX4SQ; unreadable serial | [Daikin DX4SQ product warranty information](https://daikincomfort.com/products/heating-cooling/whole-home-systems/air-conditioners/dx4sq): the product page states 60-day registration for its stated enhanced warranty. Model-specific policy is not generalized to all Daikin equipment. | 2026-03-02 |
| Rheem | 2026-01-01; unreadable model and serial | [Rheem warranties](https://www.rheem.com/warranties/): provides warranty registration and lookup, but the reviewed official HVAC page does not state one deadline applicable to every product. | No universal date supported |
| Goodman in California | 2026-01-01; unreadable model and serial; California | [Goodman HVAC Learning Center](https://www.goodmanmfg.com/resources/hvac-learning-center): Goodman says California residents do not need to register to get the rights/remedies of registered owners. That is a registration policy exception, not proof that this synthetic unit is covered. | No registration-required deadline |
| Lennox in Florida | 2026-01-01; unreadable model and serial; Florida | [Lennox product registration](https://www.lennox.com/residential/owners/register-and-review/product-registration/index): Florida homeowners automatically receive default parts-only Extended Limited Warranty; they have 60 days to change to the alternative parts-and-labor coverage. | 2026-03-02 change-option date; unit remains uncertain |

The manufacturer pages were opened/reviewed on 2026-10-11. The test file
contains the corresponding source URLs beside every frozen brand case. The
synthetic inputs do not represent a real homeowner, product, or warranty lookup.

## Test intent

- The brand policy window may produce a reminder date, but model/serial
  uncertainty must keep `result` at `uncertain — please check` and
  `registration_action` at `hold`.
- A registration exception must not be presented as a positive unit match or
  coverage determination.
- A missing or unreadable model/serial never becomes registration-ready.
- Rheem remains without a general deadline because the reviewed official page
  does not support one.
- The Lennox Florida case checks that the documented 60-day coverage-choice
  window remains visible even where registration itself is not required.

No portal, Jobber account, customer record, or email was accessed.
