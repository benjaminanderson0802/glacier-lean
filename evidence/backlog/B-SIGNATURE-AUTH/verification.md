# B-SIGNATURE-AUTH verification

Date: 2026-10-10; branch: `card/B-SIGNATURE-AUTH`

## Drift check

- Advances PH7.2 and PH12.6 as scoped work only. PH7 is owner-approved complete; PH12 depends on PH5 and PH9, which remain in progress. This work makes no phase-exit or NORTHSTAR status claim.
- Serves P-SECURE and P-CONTROL through M-SECURITY and M-AUDIT.
- Reuses the standard-library HTTP server, SQLite, the existing scoped signature request ID, and Glacier's existing local-Origin/Host patterns. No new dependency or route was added to Glacier's backend.
- Acceptance was frozen independently before implementation in `ventures/blocks/customer/tests/unit/test_B-SIGNATURE-AUTH.py`: unauthenticated success access, forged Host, forged Origin, replay rejection, and an authorized same-origin synthetic signature flow.

## Results

- Pre-change independent black-box run: 3 failed, 2 passed. The failures reproduced unauthenticated `/customer/success`, forged Host on signature review, and forged Origin on signature submission. Same-origin signature completion/replay rejection and default loopback binding passed.
- Post-change command: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests`
- Result: **17 passed**. The independent frozen file accounts for 5 checks. Added regression checks prove a checkout token is bound to its Stripe session and is one-time, and that non-loopback binds are refused. Existing customer tests were not edited.
- `git diff --check`: passed.
- Disposable standalone-server subprocess smoke, with `GLACIER_HOME` and data directory under a temporary directory and a synthetic text document: server announced `127.0.0.1:39861`; unauthenticated success GET 403; forged-Origin signature POST 403; authorized review GET 200; authorized signature POST 200; replay POST 400; one signed PDF and one audit JSON were written.
- A separate local fixture-through-server checkout-return smoke used a synthetic Stripe response and temporary customer database: authorized return GET 200, replay GET 403. No request went to Stripe or another external service.

## Evidence limits

All documents, customer records, checkout responses, and signature outputs were synthetic and local. This is fixture-through-server evidence, not a real Stripe, customer, owner-hardware, or production signature. No owner signed or published anything. PH7.2 and PH12.6 remain unchanged in NORTHSTAR; the integrator owns checkpoint evidence and status updates.
