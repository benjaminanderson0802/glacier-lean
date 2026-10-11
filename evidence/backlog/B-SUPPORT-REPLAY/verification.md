# B-SUPPORT-REPLAY verification

## Acceptance and drift check

- Checkpoint: PH12.6; no phase exit or NORTHSTAR status change is claimed.
- Properties/metrics: P-LOOPS and P-CONTROL; M-AUDIT and M-SURVIVE.
- Dependencies PH5 and PH9 remain in progress; the assigned card permits parallel work.
- Existing-tool choice: SQLite and a stable email Message-ID; no new service or dependency.
- Acceptance: with only a local fake SMTP sender, concurrent sends make at most one attempt; a transport error after fake acceptance leaves an auditable uncertain draft and a retry is blocked until reconciliation; no real mail is sent.
- An independent, spec-only evaluator found the supplied acceptance sufficient and made no edits.

## Reproduction before implementation

Using a temporary SQLite database and a two-thread fake sender blocked at a barrier produced **2 transport attempts** for one approved draft. The draft ended as `sent`.

Using a fake sender that recorded acceptance and then raised `TimeoutError`, followed by a retry, produced **2 accepted attempts** while the draft remained `pending_approval`.

The existing suite before changes passed: `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests` → **17 passed**.

## Verification after implementation

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests` → **21 passed**.
- `git diff --check` → passed.
- Tests use synthetic support messages, temporary SQLite files, and fake SMTP callbacks. They verify one concurrent attempt, stable persisted outbound identity, sent/uncertain audit events, retry blocked before reconciliation, reconciliation outcomes, and migration of an existing database.
- `npm run live` started the real backend in a temporary `GLACIER_HOME`; `/api/health` returned HTTP 200. The wrapper then stopped because this worktree has no `glacier/web/node_modules/vite/bin/vite.js`. The customer venture block has no backend endpoint, so this startup check does not exercise support delivery.
- No real mail, customer account, or external service was used.
