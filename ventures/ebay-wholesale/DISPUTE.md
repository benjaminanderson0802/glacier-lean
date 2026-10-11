# Dispute: manifest owner-step count

Date: 2026-10-11

The venture test `ventures/ebay-wholesale/tests/test_ebay_wholesale.py::test_manifest_is_valid_and_exactly_one_prelaunch_step` asserts that `venture.json` has exactly one `your_steps` entry. The owner request for card P-RESALE explicitly requires the eBay steps to be separated into: (1) eBay seller and payout verification, (2) developer keys, and (3) submitting the prefilled supplier applications. Combining these as one manifest entry would conceal the requested action boundaries and no longer describe the three distinct setup tasks.

The test was not edited because independent checks are not worker-owned. The manifest follows the current owner instruction and has three steps. Targeted test result on 2026-10-11: 1 failed (the step-count assertion), 6 passed. Reconcile this test in a separately assigned independent-test card.
