# B-TEMPLATE-PREVIEWS — Generate missing template previews from their real graphs

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-TEMPLATE-PREVIEWS`; never push.

## Scope

Allowed edits: `templates/previews/tpl-email-inbox-note.{png,sha256}; templates/previews/tpl-email-search-note.{png,sha256}; templates/previews/tpl-local-data-pipeline.{png,sha256}; templates/previews/tpl-item-processor.{png,sha256}`. Also allowed: `evidence/backlog/B-TEMPLATE-PREVIEWS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **template-artifacts**. Artifact-only scope avoids U-SCREENS and E-PH5 product code. Run the renderer in a disposable copy if it rewrites other previews; bring back only the four named pairs. Recheck template hashes immediately before commit.

## Goal and evidence

Fresh T-FIND run fails the existing preview acceptance check first at tpl-email-inbox-note. Four added template graphs have no committed preview pairs.

Use the existing renderer to generate the four missing preview images and source hashes. Read template JSON and UI code only; write just the named artifact pairs. Preserve all existing templates and checks.

Read first:

- [templates/test_templates.py](../../templates/test_templates.py) (test_every_template_has_a_current_graph_preview)
- [glacier/web/scripts/render-template-previews.mjs](../../glacier/web/scripts/render-template-previews.mjs)

## Drift check

- Checkpoint: **PH10.2**. Properties: **P-USABLE, P-VERIFY**. Metrics: **M-VERIFIED, M-TTFA**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing graph renderer and pinned browser/PDF dependencies; no AI-generated diagram, new theme or rendering system.
- Value/effort estimate: **3/5 value ÷ 1 effort units = 3.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

The unchanged test_every_template_has_a_current_graph_preview passes. Independently compare each image with its source nodes/edges and confirm source hashes. Report the separate existing template-count/layout failures without deleting templates or altering assertions.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q templates/test_templates.py::test_every_template_has_a_current_graph_preview`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
