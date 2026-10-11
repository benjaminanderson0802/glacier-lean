# Progress — Carpenter's goods

## Drift check

- Checkpoint: PH12.20. Its PH5 and PH9 dependencies are marked at exit in `NORTHSTAR.yaml`.
- Defining properties and metric: P-USABLE / M-INTERVENE through a two-step owner checklist, with P-VERIFY for checked calculations.
- Existing coverage: the local scripts already prepare drafts from product-sheet CSV and calculate commissions from Etsy/Shopify order CSV exports. The remaining acceptance gap was that the header-only product sheet lacked the filename pattern the independent check discovers. Python's standard-library CSV parser covers the workflow without a new dependency.
- Acceptance written first: `tests/test_csv_workflow.py` exercises product CSV → both listing drafts and Etsy + Shopify exports → paid-only commission summary; the requested venture pytest suite must pass.

PH12.20 remains unverified. This card adds the acceptance-discoverable `templates/product-sheet-template.csv` name for the existing one-row product-sheet template; `templates/product-sheet.csv` remains available as a compatible copy. The CLI produces separate Etsy and Shopify drafts from the CSV, and the README explains that the drafts remain unpublished pending the owner's manual review and publication step. Commission calculation accepts Etsy and Shopify order-level CSV exports and reports paid totals, the written rate calculation, excluded rows, and the need to confirm the eligible amount against the agreement.

Owner actions remain owner-only: both parties sign; the owner obtains and supplies exports; the owner reviews and manually publishes listings; the owner compares commission output with settlements before invoicing or paying. The owner checklist is condensed to two steps in the venture manifest.

Fixture acceptance coverage is in `tests/test_csv_workflow.py`; it uses synthetic data and does not establish live Etsy/Shopify compatibility. No signed agreement, real order export, current completed-sale comparison, public listing, or real shop action was used. In a disposable real backend, both flows installed and the `{repo}` placeholder resolved, but neither flow completed: the commission flow was refused because it has no environment acceptance check (I-04 requires an independent author for that check); the listing flow reproducibly skipped draft generation after its input approval and failed its output check. The first listing smoke sent duplicate approvals; the fresh retry sent each once and reproduced the failure. The listing runtime issue is outside this venture card's code lane. See `PROOF.md`; the earlier `{repo}` issue remains documented in claim `CLM-PH12-20-CWD-REPO` until independently verified with owner data.

`~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods/tests/acceptance/test_v_carpenter2.py::test_product_sheet_csv_generates_etsy_shopify_drafts_without_publishing -q --runxfail` — **1 passed**. `~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods -q` — **10 passed, 2 xpassed**. These are synthetic fixture checks; manifest dry-run passed previously, while real-runtime verification remains incomplete as described above.

The optional broader `pytest ventures -q` collection did not start because unrelated recall-actor and utility-audits tests could not import their `src.sources` and `scripts.utility_audit` modules; details are in `PROOF.md`.

The two real-runtime blockers need claims routed outside the `ventures/**` card lane; they are recorded here for handoff.
