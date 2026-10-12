# Dispute: manifest owner-step count

Date: 2026-10-11

The venture test `ventures/depop-resale/tests/test_depop_resale.py::test_manifest_is_valid_and_has_one_human_step` asserts that `venture.json` has exactly one `your_steps` entry. The owner request for card P-RESALE explicitly requires Depop steps to be separated into: (1) buy stock within ceilings, (2) take original photos and enter facts, and (3) approve drafts and list manually. Combining these as one manifest entry would conceal the requested action boundaries and no longer describe the three distinct owner tasks.

The test was not edited because independent checks are not worker-owned. The manifest follows the current owner instruction and has three steps. Targeted test result on 2026-10-11: 1 failed (the step-count assertion), 5 passed. Reconcile this test in a separately assigned independent-test card.
