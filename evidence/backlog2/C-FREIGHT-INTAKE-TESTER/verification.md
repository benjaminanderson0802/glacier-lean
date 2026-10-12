# C-FREIGHT-INTAKE-TESTER verification

## Drift check and acceptance, recorded before implementation

- Checkpoint: PH12.14 (freight claims). PH5 and PH9 remain in progress; PH12 work is explicitly owner-authorized by this card.
- Properties and metrics: P-VERIFY / P-CONTROL; M-VERIFIED / M-AUDIT.
- Existing tools: ShipStation CSV intake, source templates, and pytest. No carrier integration is used by this check.
- Acceptance: synthetic source rows and customer inputs must map to the generated shipment, damage, document, carrier-rule, and deadline fields; missing or unsupported facts must remain uncertain; output must not claim recovery or filing, submit a claim, or send mail.

## Commands and results

```text
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests/acceptance/test_C-FREIGHT-INTAKE-source-packet.py
1 failed, 5 passed

~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests
1 failed, 40 passed
```

Both failures are the same acceptance assertion in `test_missing_and_unsupported_source_rows_stay_uncertain_and_unfiled`.

## Finding

For the synthetic `Mystery Parcel Co` shipment, packet generation returns `result: "match"`, while `carrier_claim_guidance.template_id` is `manual-review`, `filing_deadline` is null, and the rule source list is empty. The test supplies otherwise complete synthetic intake and documents, so the unsupported carrier itself is the fact that must prevent a `match`. The packet still includes an email draft despite that unsupported source. The required uncertainty and no-draft assertions therefore fail.

The tests also pass for UPS scheduled-delivery +60 days, FedEx domestic shipment-date +60 days, FedEx international shipment-date +21 days, conditional LTL delivered-date +9 months, shipment and tracking ID mapping, confirmed damaged-item arithmetic, attached source-document paths, official source hosts, unsent/non-authorizing packet drafts, and uncertainty for missing intake or photos. All evidence and shipment values are synthetic fixtures; passing these checks is fixture-through-engine proof only, not carrier/customer evidence.

The unsupported-carrier packet currently includes an email draft even though its rule is manual review with no source or calculated deadline. No carrier request, claim filing, or customer message was made. Runtime/parser files and existing checks were not changed. The finding needs correction in the claim-packet engine outside this tester card's allowed edit list; checkpoint status was not changed.
