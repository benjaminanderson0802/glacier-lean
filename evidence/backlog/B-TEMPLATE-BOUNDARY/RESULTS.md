# B-TEMPLATE-BOUNDARY evaluator results

## Drift check

- Checkpoint: PH10.4, independent evidence only; this card does not claim a PH10 exit.
- Dependencies: PH10 depends on PH8 and PH9, both still in progress. The launch contract explicitly allows this scoped evaluator to start while those phases are in progress.
- Properties / metrics: P-SECURE and P-CONTROL; M-SECURITY and M-AUDIT.
- Existing tools: public template APIs, existing manifest and pytest. No new framework or dependency.
- Acceptance written before implementation: see the module docstring in `tests/backlog/test_template_boundary.py`.

## Verification

`~/w/glacier-lean/.venv/bin/python -m pytest -q tests/backlog/test_template_boundary.py -s` starts the real FastAPI backend with a disposable `GLACIER_HOME`, bearer token, synthetic input flows, and a copied bundle directory. It failed four related assertions: approval accepted a pending template after its reviewed command changed from `date -Is` to `curl https://example.invalid`, and accepted a second template after an `email_send` node was added after review. Both changed templates appeared in the gallery as installable. The evaluator did not run either imported flow, send email, or make a network request.

The same run passed the other recorded checks: unchanged reviewed bundle import was accepted and pending; digest-tampered bundle was disabled and omitted its template body; unknown step type was rejected; a known side-effect capability remained pending and absent from the gallery before approval; encoded proposal traversal returned 404. Exact API status/body pairs and the disposable backend's audit rows are in `template-boundary-api.json`.

`~/w/glacier-lean/.venv/bin/python -m pytest -q templates` finished **2 failed, 5 passed**. The existing failures are: the gallery test expects 16 templates but reads 20, and the environment contract test rejects an x coordinate of 300 as not divisible by 260. Similar failures are already recorded in `CLM-2026-10-10-E-PH9-PROJECT-BOARD`; this tester made no changes to templates or existing checks. Full output is in `templates-pytest.log`.

## Evidence classification and routing

This is real backend/API evidence using disposable local state and synthetic flows. The manifest tamper was performed only against the copied fixture bundle. No customer data, external service, model, or network destination was used. The command replacement bug is routed to the PH10.4 template import owner in `vault/claims/2026-10-11-b-template-boundary-command-swap.md`.

No checkpoint status was changed. No anti-pattern requiring correction was found: the new check exercises the public API, and neither existing tests nor product code were changed.
