---
id: claim-b-utility-form-scope
filed_by: Codex
run_id: local-card-gf-B-UTILITY-FORM
node_id: utility-form-renderer
checkpoint: PH12.18
kind: unclear_spec
summary: The card's allowed implementation paths do not exist in the assigned worktree.
evidence: "The assigned card permits edits under `new ventures/utility-audits/...`, but this checkout has no `new ventures/` directory. Existing utility implementation, tests, and docs are under `ventures/utility-audits/`; ORCHESTRATION wave 6 authorizes the ventures lane but does not amend the card's exact allowed paths."
attempts_made: 1 read-only path inspection; no files outside claim scope changed.
status: filed
assigned_to: researcher
resolution: ""
resolution_evidence: ""
---

Before implementation, confirm whether this card authorizes the corresponding existing paths under `ventures/utility-audits/`. Do not create a parallel `new ventures/` tree: the current preparation command, fixtures, flows, and owner guide all use the existing `ventures/utility-audits/` module.

The card also requires an independent evaluator to freeze any missing acceptance case. The existing utility acceptance checks judge JSON preparation, not rendered PDF fields. Assign or identify that evaluator before adding product tests; the builder must not edit existing acceptance files.
