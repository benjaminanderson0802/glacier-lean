# CPSC data prep progress

Card V-CPSC2 advances PH12.9. PH12 depends on PH5 and PH9, whose phase exits
are recorded as reached; wave 6 assigns this venture in parallel. It serves
P-CONTROL and P-USABLE, with M-VERIFIED and M-INTERVENE, by keeping customer
review, certification, and filing under human control. Existing CPSC registry
and feed tools cover official formats and data; this venture supplies the
local document-preparation and review glue around them.

**Status: ready for owner review; not live.** Batch preparation, source-linked
gaps, customer certification, exact-template CSV generation, the importer
status board, test-mode checkout, daily source refresh, code-page preview, and
broker approval flows are implemented. The batch flow's file-ready approval
edge was corrected after a live engine run showed it skipped draft preparation.
The code-page preview now flattens the shared feed's nested record shape and
uses its fetch timestamp. The focused test is in
[`tests/test_code_pages.py`](tests/test_code_pages.py); no acceptance checks
were edited.

Live CPSC feed checks on 2026-10-10 returned 589 HTS rows, 130 citation and
testing-exception rows, one Product Registry template record, and 10,047
Recalls API rows. Repeated syncs reported `changed: false` with no canary
alerts. A live Glacier engine run completed the feed-refresh flow; another
built 589 code-page previews and waited at the owner publication approval.
Evidence: [`PROOF.md`](PROOF.md),
[`evidence/live-feed-canaries-2026-10-10.json`](evidence/live-feed-canaries-2026-10-10.json),
and [`evidence/glacier-engine-flows-2026-10-10.json`](evidence/glacier-engine-flows-2026-10-10.json).

The batch flow ran in Glacier with a synthetic CSV and local `qwen3:1.7b`
second extraction. Six required fields matched; one remained uncertain, the
result had 89 gaps, no upload CSV was released, and the flow waited at the
certification approval. This is engine and fixture evidence, not customer
evidence. The broker flow remains waiting at its lawyer-opinion gate. No
customer batch, certification, Product Registry upload, or filing was
performed. Cited operative CPSC pages were reachable; a fictional URL in an
acceptance-only fixture returned an internal error and remains untouched.

Verification on 2026-10-10:

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/cpsc-prep -q` — 21 passed, 1 skipped.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` — 21 passed.
- The full venture flow evidence is recorded with run IDs and node outputs; the local independent extraction is explicitly labeled.

One owner step remains, described in [README.md](README.md): obtain trade
counsel's written opinion, select the broker price and configure live payment
or account details, sign any broker agreement, and review/certify/file real
batches as legally authorized. The owner also approves optional public
code-page publication. Glacier does not perform those actions.

No PH12 checkpoint status was changed. PH12.9 is not marked released; owner
legal, commercial, certification, and publication steps remain open.
