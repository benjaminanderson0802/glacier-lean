# Progress — Carpenter's goods

PH12.20 remains unverified. This card adds an owner-fillable commission agreement and plain-language summary, a one-row product-sheet CSV template, and CLI support to produce Etsy/Shopify drafts from that CSV. Commission calculation now accepts Etsy and Shopify order-level CSV exports and reports paid totals, the written rate calculation, excluded rows, and the need to confirm the eligible amount against the agreement.

Owner actions remain owner-only: both parties sign; the owner obtains and supplies exports; the owner reviews and manually publishes listings; the owner compares commission output with settlements before invoicing or paying. The owner checklist is condensed to two steps in the venture manifest.

Fixture acceptance coverage is in `tests/test_csv_workflow.py`; it uses synthetic data and does not establish live Etsy/Shopify compatibility. No signed agreement, real order export, current completed-sale comparison, public listing, or real shop action was used. In a disposable real backend, both flows installed and the `{repo}` placeholder resolved, but neither flow completed: the commission flow was refused because it has no environment acceptance check (I-04 requires an independent author for that check); the listing flow reproducibly skipped draft generation after its input approval and failed its output check. The first listing smoke sent duplicate approvals; the fresh retry sent each once and reproduced the failure. The listing runtime issue is outside this venture card's code lane. See `PROOF.md`; the earlier `{repo}` issue remains documented in claim `CLM-PH12-20-CWD-REPO` until independently verified with owner data.

`~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods -q` — **9 passed**. Manifest dry-run passes; real-runtime verification is incomplete as described above.

The optional broader `pytest ventures -q` collection did not start because unrelated recall-actor and utility-audits tests could not import their `src.sources` and `scripts.utility_audit` modules; details are in `PROOF.md`.

The two real-runtime blockers need claims routed outside the `ventures/**` card lane; they are recorded here for handoff.
