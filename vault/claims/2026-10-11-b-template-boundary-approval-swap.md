---
id: CLM-2026-10-11-B-TEMPLATE-BOUNDARY-APPROVAL-SWAP
filed_by: B-TEMPLATE-BOUNDARY
run_id: null
node_id: null
checkpoint: PH10.4
kind: bug
summary: Template approval accepts commands or capabilities changed after review
evidence: "tests/backlog/test_template_boundary.py::test_template_provenance_and_approval_boundary_on_real_backend; evidence/backlog/B-TEMPLATE-BOUNDARY/template-boundary-api.json"
attempts_made: 1
status: filed
assigned_to: builder_b (PH10.4 template import owner)
resolution: null
resolution_evidence: null
---

The independent real-backend check imported the unchanged, reviewed `tpl-daily-report`
bundle whose reviewed command was `date -Is`. In the disposable `GLACIER_HOME`, the pending proposal's
command was then replaced with `curl https://example.invalid` while leaving the
stored `commands_for_review` snapshot unchanged. `POST
/api/templates/import/{proposal_id}/approve` returned HTTP 200 with
`{"id":"…","status":"approved"}`. A following `GET /api/templates` returned
the imported template as `review_status: approved`, `installable: true`, with the
changed command. No imported flow was run and no network request was made.

The same check added an `email_send` capability after review to a second pending
proposal. Approval also returned HTTP 200 and the added capability appeared in the
installable gallery entry. No email was sent.

This means approval is not bound to the reviewed command or capability content; the
changed command and added capability can become executable authority after one approval. The retained
API response bodies and audit rows (`template.reviewed`, `template.approved`) are in
the evidence artifact above. The API-only encoded traversal case returned 404, the
unknown step type was rejected, and an unmodified side-effect capability remained
pending and absent from the gallery before approval.

The PH10.4 template import owner should reproduce the replacements through the
current public API and make approval verify the exact reviewed template and
capability snapshot. The evaluator will rerun its frozen check after the builder
provides a candidate; this claim does not authorize product changes by the tester.
