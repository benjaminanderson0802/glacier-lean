---
id: claim-ph12-12-recall-output-vocabulary
filed_by: Codex
run_id: local-card-gf-V-RECALL
node_id: recall-output-contract
checkpoint: PH12.12
kind: unclear_spec
summary: Recall checker output wording conflicts between the venture section and the rules for every venture.
evidence: ventures/SPEC.md global output vocabulary requires `no match found in [sources] as of [date]`; Spec: Recall checker says `no match in CPSC, NHTSA, FDA and FSIS as of [date]`; focused acceptance test currently asserts the latter and fails against the global vocabulary implementation.
attempts_made: 1; stopped because the spec itself conflicts and I-04 forbids editing the acceptance check.
status: filed
assigned_to: researcher
resolution: ""
resolution_evidence: ""
---

The matching implementation follows the global vocabulary because it applies to every venture. One builder-authored acceptance assertion was written from the venture-specific example before the global wording conflict was recognized. It failed on the exact mismatch; the implementation was not changed to the less-specific wording and the test was not edited. A clean resolution is for the integrator/owner to clarify which wording should be canonical, then update the independently owned check or contract before the release check is rerun. No PH12.12 completion claim is made.
