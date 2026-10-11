# B-MAIL-SECRETS proof

## Drift check and acceptance

- Checkpoints: PH7.3 and PH12.7. PH7 is recorded complete. PH12 depends on PH5/PH9, which remain in progress; the launch ledger explicitly authorizes this scoped work in parallel, and this proof makes no phase-exit claim.
- Properties and metrics: P-SECURE / M-SECURITY and P-CONTROL / M-AUDIT.
- Existing tools: reused Glacier `secrets_store` and the existing pinned `httpx` dependency. No paid service or new dependency was added.
- Acceptance, frozen before implementation by the independent evaluator: resolve Lob keys through Glacier Secrets; ignore environment credentials; allow authenticated calls only to `https://api.lob.com/v1`; reject live keys, unapproved base URLs, redirects and secret-bearing errors; preserve keyless render-only output and test-key plus explicit-approval behavior; expose injected secret and transport seams for offline tests.

## Reproduction

Before implementation, the existing mail suite passed **4 tests**. A local-only `urlopen` replacement then captured a synthetic test key being sent to `https://unapproved.invalid/collect` when `LOB_API_BASE_URL` was set to that host (`authorization_sent: true`). No network request was made during reproduction.

The new ordinary unit tests were run before the feature change and failed on the missing secret getter and transport parameters, confirming the scoped gap. Existing acceptance files were not changed.

## Verification

All credentials and addresses below were synthetic; transports were fakes.

| Check | Command / method | Result |
| --- | --- | --- |
| Mail module suite | `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests` | **9 passed** |
| Independent acceptance evaluator | `~/w/glacier-lean/.venv/bin/python evidence/backlog/B-MAIL-SECRETS/independent_acceptance.py` | **8 passed**; validates keychain lookup, no-key render-only/no HTTP, live-key rejection, approval gate, authenticated validation + postcard sequence, host/path restrictions, no redirect follow, and error redaction |
| Real backend fixture-through-engine | Started Uvicorn on a unique loopback port with a disposable `GLACIER_HOME`; `/api/health` returned `{"ok": true}`. Saved a synthetic `test_` Lob value through the real `secrets_store` using an in-memory keyring, then called the mail postcard engine with a fake transport. | **`sent_test`**, exactly `GET /v1/addresses/validate` then `POST /v1/postcards`; no Lob network request; temporary home removed |
| Patch whitespace | `git diff --check` | clean |

The backend startup is real-backend evidence. The Lob calls are fixture-through-engine evidence, not Lob account, customer, production or live-network evidence.

## Owner steps and limits

No account, key, mail, purchase, filing or external write was used. No NORTHSTAR status or acceptance check was changed. The integrator still owns checkpoint status/evidence updates and the shared test board at integration.
