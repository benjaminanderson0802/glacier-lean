---
id: CLM-2026-10-10-PH12-14-FILER-PLAYWRIGHT-MISSING
filed_by: Codex
run_id: card/gf-V-FREIGHTCSV
node_id: ventures.blocks.filer
checkpoint: PH12.14
kind: environment
summary: The required freight and shared-block test command cannot pass because three shared portal-filer tests cannot resolve the Playwright Node dependency.
evidence: "`~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims ventures/blocks -q`: 80 passed, 3 failed; all failures are `ventures/blocks/filer/tests/test_filer_acceptance.py` with Node `MODULE_NOT_FOUND` at `ventures/blocks/filer/runner.mjs:8`."
attempts_made: 0; stopped because the missing dependency is outside the freight/connector lane.
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

The failing tests are `test_approved_submit_saves_confirmation_and_replay_does_not_double_file`, `test_prepare_fills_multistep_form_and_never_submits`, and `test_submit_requires_approval`. All three fail before exercising the filer because Node cannot resolve the runner's Playwright dependency. This card does not own `ventures/blocks/filer`; no package installation, filer edit, or test edit was attempted. Resolve the shared test environment/dependency and rerun the original combined command before treating PH12.14 as fully verified.
