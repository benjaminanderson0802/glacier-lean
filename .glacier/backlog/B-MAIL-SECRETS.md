# B-MAIL-SECRETS — Keep mail credentials in the keychain and on the approved host

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-MAIL-SECRETS`; never push.

## Scope

Allowed edits: `ventures/blocks/mail/engine.py`. Also allowed: `evidence/backlog/B-MAIL-SECRETS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **mail**. No active-card dependency; take the exclusive lane before editing.

## Goal and evidence

Mail currently reads LOB_API_KEY and an arbitrary LOB_API_BASE_URL from environment variables, unlike the customer block keyring path.

Resolve credentials through Glacier Secrets, confine authenticated transport to the approved endpoint, and preserve test-key-only and explicit-approval behavior. Provide a credential-free mock transport seam for ordinary unit tests.

Read first:

- [ventures/blocks/mail/engine.py](../../ventures/blocks/mail/engine.py) (_api_url, _lob_request, verify_address, postcard)

## Drift check

- Checkpoint: **PH7.3, PH12.7**. Properties: **P-SECURE, P-CONTROL**. Metrics: **M-SECURITY, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing secrets_store and HTTP transport; no paid service adoption or live Lob request.
- Value/effort estimate: **5/5 value ÷ 2 effort units = 2.50**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent checks reject live keys and unapproved hosts/redirects, keep secrets out of error output, and prove keyless render-only output remains available. Existing mail acceptance stays unchanged.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/mail/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
