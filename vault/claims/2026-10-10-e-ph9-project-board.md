---
id: CLM-2026-10-10-E-PH9-PROJECT-BOARD
filed_by: E-PH9
run_id: null
node_id: health
checkpoint: PH9.1
kind: bug
summary: Existing template acceptance failures block current self-build verification
evidence: evidence/ph9/project-tests.log
attempts_made: 0
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

At source c17f52c0fbb4c9cc3bb49baaf7acec116d83c3e4, the unchanged command `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q glacier/importers templates bench tools/scan tools/catalog` ended **3 failed, 76 passed in 30.16s**:

- `test_gallery_has_the_sixteen_requested_templates`: 20 templates exist; the independent test expects 16.
- `test_templates_follow_the_environment_contract_and_catalog`: a node x coordinate is 300, which fails the required 260-grid alignment.
- `test_every_template_has_a_current_graph_preview`: `tpl-email-inbox-note` lacks a generated preview.

These are existing feature-flow gates. No feature branch should merge under the saved flow while these gates fail. Templates and their acceptance checks belong to other lanes; E-PH9 makes no fix attempt and does not modify the tests. The integrator should route the template implementation defects and the spec/count disagreement to their respective builder and independent test owner. The failing evidence remains committed even if another worker later fixes their branch.

PH9.2 historical merge IDs (`9cdd84d`, `b6e8095`, `deea119`) are recorded in `evidence/live/selfbuild_first_card.md`, but their Git objects are not available in this checkout (see `evidence/ph9/historical-objects.json`). This card therefore treats those as historical records, not freshly reproduced shipments. It does not downgrade or upgrade NORTHSTAR on a self-report. The integrator retains responsibility for reconciling phase closure with original practice artifacts and PH5 dependencies.
