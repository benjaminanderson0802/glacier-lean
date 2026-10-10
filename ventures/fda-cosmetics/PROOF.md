# Proof — FDA cosmetics listing preparation

## Acceptance check written first

`/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/fda-cosmetics/tests/test_fda_cosmetics.py`

Current result: **4 failed, 3 passed**. The two success-path tests and the reader-uncertainty test use `label.pdf` as their ingredient document without creating the file. The production code correctly leaves a missing label uncertain, so those tests do not reach their reader mocks. Claim [CLM-2026-10-10-PH12-15-LABEL-TEST-FIXTURE](../../vault/claims/2026-10-10-ph12-15-label-test-fixture.md) records this blocker. The task is parked per NORTHSTAR escalation; no checkpoint is marked done.

The acceptance check is intended to verify that complete customer-confirmed fields create a local SPL ZIP with FDA cosmetic listing document type and source-cited rules results; uncertain reader output and missing fields remain uncertain and block ZIP generation; parsing an FDA response does not submit anything; and the manifest/flow leaves FDA signing and submission to the customer.

## Drift check

1. Checkpoint: PH12.15, FDA cosmetics listing venture.
2. Dependencies: PH12 depends on PH5 and PH9, which are not at exit. The assigned V-FDA card explicitly authorizes this work to start; it does not authorize marking PH12.15 done.
3. Defining properties and metric: P-CONTROL and M-AUDIT. The flow never signs or submits; FDA submission remains a customer action behind a visible approval step.
4. Existing tools: the shared Shopify connector, reader, rules checker, and deadline tracker cover the platform reads, extraction, cited field checks, and reminders. The venture-specific glue is needed to map those blocks into an FDA packet. No shared block or dependency was added.
5. Acceptance test: the focused venture suite listed above, written before feature implementation. It is currently failing because the temporary label fixture is missing; see the linked claim.

## Anti-pattern review

No governance layer or platform runtime code was added. The task adds working venture scripts and flows, and the tests check packet contents and customer-only submission behavior. The test failure and imported reader test mismatch are recorded as claims. PH12.15 remains in progress; no completion status is claimed.

## Imported block checks

- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/reader/tests/test_acceptance.py` — **1 failed, 2 passed**. The shared reader returns `ABC-7` with `uncertain: true` for a disagreement; its test expects the value to be `None`. This is outside this card's lane; claim [CLM-2026-10-10-PH12-15-READER-CONFLICT-CONTRACT](../../vault/claims/2026-10-10-ph12-15-reader-conflict-contract.md) is assigned to B1.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/rules/tests/test_acceptance.py` — **3 passed**.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py` — **11 passed**.
- `/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only fda-cosmetics --dry-run` — both flows validated.
- A synthetic packet was generated in a temporary directory and validated against FDA's published `SPL.xsd` (2016 schema package) with `lxml.etree.XMLSchema`; output: `FDA SPL XSD valid: True`. The schema package was fetched from FDA only into `/tmp` for this check and is not bundled. This verifies XML schema structure, not the FDA portal's full technical or business validation.

## FDA references

- [FDA Form FDA 5067](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products/form-fda-5067-cosmetic-product-listing) documents required responsible-person, product category, facility, and ingredient fields.
- [FDA SPL Implementation Guide with Validation Procedures](https://www.fda.gov/media/84201/download), cosmetic listing section 36, documents SPL product listing and XML validation rules.
- [FDA Cosmetics Direct](https://www.fda.gov/cosmetics/registration-listing-cosmetic-product-facilities-and-products) imports SPL ZIPs and performs its own initial validation.

## Live verification still needed

No real Shopify credentials or brand product label were available. No FDA portal account was created, no filing was signed or submitted, no live Glacier run was completed, and no screenshot evidence was captured. A separate test fixture fix and independent review are required before PH12.15 can be considered verified.
