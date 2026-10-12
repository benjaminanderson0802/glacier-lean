---
id: CLM-2026-10-11-C-APIFY-MS-LA-UNCERTAIN-BILLING
filed_by: C-APIFY-MS-LA-TESTER
run_id: null
node_id: null
checkpoint: PH12.10
kind: bug
summary: Mississippi and Louisiana Actors emit the billable event for uncertain lookup results
evidence: "Independent acceptance tests at `ventures/apify-tools/tests/acceptance/test_independent_actor_billing.py::test_uncertain_or_unverifiable_lookup_does_not_emit_billable_event[uncertain]` and `ventures/apify-tools-louisiana/tests/test_independent_actor_billing.py::test_uncertain_or_unverifiable_lookup_does_not_emit_billable_event[uncertain]` fail: each runner calls `charge` for `verification_state: uncertain`. Full logs: `evidence/backlog2/C-APIFY-MS-LA-TESTER/mississippi-pytest.log` and `evidence/backlog2/C-APIFY-MS-LA-TESTER/louisiana-pytest.log`. Both Actor templates charge any first result except `unverifiable`; verified match/no-match and local-default billing tests pass."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Impact

The acceptance boundary for card C-APIFY-MS-LA-TESTER is that only successful readable lookups may emit the configured billable event. An incomplete but readable detail result is labeled `uncertain` by the source adapters, yet both copied Actor templates charge it. This is distinct from a source outage, which is `unverifiable` and is not charged. The existing pricing review also records that uncertain records currently can be charged.

## Required resolution

Have the Actor owner review whether the event guard should require `verification_state == "verified"` for both Actors. If accepted, update the product code in its assigned lane and rerun these independent checks. This tester card does not modify Actor code. Do not advertise that uncertain results are free until the behavior is corrected and verified.
