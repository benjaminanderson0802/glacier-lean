# C-CLOSEOUT-PILOT-TESTER evidence

Date: 2026-10-11. This is fixture-through-generator evidence only; it contains
no customer records and does not establish buyer demand.

## Drift check

- Checkpoints: PH12.8 shared platform connectors and PH12.22 integration audit.
  PH12 remains in progress because PH5 and PH9 are still in progress; the
  assigned card explicitly authorizes this parallel audit.
- Properties and metrics: P-VERIFY, P-USABLE, M-VERIFIED, M-INTERVENE.
- Existing tools: the current closeout generator, pytest, and synthetic
  Jobber-shaped JSON fixtures. No dependency or product code was added.
- Acceptance first: frozen cases in
  `ventures/job-closeout/tests/acceptance/test_C_closeout_pilot.py` cover five
  accurate packets, absent values, a malformed completion date, partial pages,
  GraphQL errors, source outage, and rate limiting. Assertions check source
  retention, visible uncertainty, reviewable Markdown/PDF, no compliance
  certification claim, and no external delivery action.

## Results

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/job-closeout/tests/acceptance/test_C_closeout_pilot.py` — **7 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/job-closeout/tests` — **28 passed, 1 skipped**.
- Full command output is retained in `acceptance.log` and `venture-suite.log`.
- The five synthetic completed jobs produced five Markdown/PDF pairs. The
  supplied job, customer, mapped work/equipment/invoice fields, address and
  completion date were retained in both formats. Output reported
  `external_actions: none`; fixture tests block network connections and reject
  live connector construction.
- Missing and malformed values rendered as `uncertain — please check`.
  Incomplete page, GraphQL error, source outage and rate limit created no
  packets and returned controlled uncertain errors.

## Scope and limitations

No generator code or existing checks were edited. No customer data was used,
and no packet was sent, published, charged, or submitted. This validates the
current synthetic fixture path, not authenticated Jobber production delivery,
customer acceptance, service usefulness, or demand for the $49 offer.

The requested `ventures/job-closeout/PROOF.md` was not present in this checkout;
the directory contains `flows/evidence/.../proof.json`. This independent result
is therefore recorded here without altering venture documentation or
checkpoint status.
