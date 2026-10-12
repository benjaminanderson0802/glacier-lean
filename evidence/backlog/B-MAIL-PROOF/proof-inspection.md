# B-MAIL-PROOF inspection record

## Acceptance source

The independent evaluator froze [evaluator-case.md](evaluator-case.md) before implementation. Existing acceptance files and `CHECK.md` were left unchanged.

## Fixture-through-engine proof

- Reproduced the old truncation with 120 distinct `REVIEW-TOKEN-NNN` markers: the generated PDF contained 48 markers and omitted `REVIEW-TOKEN-119`.
- Re-rendered styled synthetic front/back content with headings, emphasis, a list, and a link into [standard-review-proof.pdf](standard-review-proof.pdf).
- PDF inspection found two pages, each with a 6 × 4 inch page box. Extracted text retained the front and back copy, the link text, the local review / not-print-ready label, and the exact synthetic return address: Fixture Sender Co., 12 Proof Lane, Suite 4, Fixtureville WI 53703.
- A 320-token long-copy example returns `blocked_overflow` with a visible reason and no proof PDF.

## Real-backend fixture proof

A disposable backend used `GLACIER_HOME=/tmp/glacier-b-mail-proof-20261010` on `127.0.0.1:53571`. A temporary one-node command flow called the shared mail helper with synthetic sender/copy data. Final run `98b8f3e66d6b` completed with `status=render_only`, `proof_kind=local_review`, dimensions `{width: 6, height: 4}`, and `proof_notice=Local review proof only; not print-ready.` Its PDF is [real-backend-fixture-proof.pdf](real-backend-fixture-proof.pdf). The configured Lob key was absent; address verification stayed uncertain and no send/order occurred.

This is a real local backend/runtime path using synthetic data. It is not customer, production, USPS, print-shop, or mailing evidence.

## Separate co-op EDDM proof

Read-only inspection of `ventures/coop-postcards/evidence/live-flow-output/postcard/fixture-eddm-2026-01-eddm-proof.pdf` found two 11.5 × 6.25 inch pages, each labelled `11.5 x 6.25 inch USPS EDDM Retail flat proof`. The co-op EDDM renderer and its tests were not changed.

## Commands

- `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests` — 12 passed.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m py_compile ventures/blocks/mail/engine.py ventures/blocks/mail/tests/unit/test_b_mail_proof.py` — passed.
- The disposable backend started with `uvicorn app:app --host 127.0.0.1 --port 53571`; `/api/health` returned `{"ok": true}`, the synthetic mail-render flow completed, and the worker-owned backend process shut down cleanly.
