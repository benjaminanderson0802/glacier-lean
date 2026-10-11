# B-CLOSEOUT-PDF — Preserve customer names and equipment text in closeout PDFs

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-CLOSEOUT-PDF`; never push.

## Scope

Allowed edits: `ventures/job-closeout/scripts/generate_packet.py; new ventures/job-closeout/PDF-NOTES.md`. Also allowed: `evidence/backlog/B-CLOSEOUT-PDF/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **closeout**. Serialize after B-CLOSEOUT-PATH because both edit the same generator. No A-CASH materials or flow edits.

## Goal and evidence

_pdf_escape normalizes then encodes ASCII with replacement, losing non-Latin customer names and symbols while Markdown retains them.

Render Unicode faithfully with an already pinned redistributable PDF/text stack where possible. Keep multipage text complete and explicitly report unsupported glyphs rather than silently corrupting facts.

Read first:

- [ventures/job-closeout/scripts/generate_packet.py](../../ventures/job-closeout/scripts/generate_packet.py) (_pdf_escape, render_pdf)
- [ventures/job-closeout/samples/job-9001.pdf](../../ventures/job-closeout/samples/job-9001.pdf)

## Drift check

- Checkpoint: **PH12.8**. Properties: **P-USABLE, P-VERIFY**. Metrics: **M-VERIFIED, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Inspect existing PDF libraries/fonts first; adopt no unpinned font or dependency and record redistribution license.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent sample names and equipment labels survive PDF extraction and visual review, including accented and non-Latin text, punctuation and long packets. Compare the PDF to the generated Markdown.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/job-closeout/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
