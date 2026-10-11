# Warranty registration proof

Acceptance command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/warranty/tests/test_warranty.py
```

Integrated suite on 2026-10-10: `17 passed`. Earlier focused output was `15 passed in 0.04s`.

Shared Jobber connector fixture check:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py
```

Integrated suite on 2026-10-10: `17 passed`. Earlier connector fixture output was `11 passed in 0.14s`.

Glacier flow validation:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.install_all --only warranty --dry-run
```

Output: all three declared flows (`hourly-intake`, `daily-deadlines`, `owner-review`) validated.

Whitespace check: `git diff --check` passed.

Real Glacier dry-run:

```sh
heavy env PYTHONPATH=<worktree-root> npm run live
GLACIER_HOME=<live-home> GLACIER_API=<live-api> ~/w/glacier-lean/.venv/bin/python -m ventures.install_all --only warranty
POST /api/environments/daily-deadlines/run
```

Output: run `2643340aff32` reached `waiting` at `review_draft`. On a synthetic Carrier fixture, the command returned a deadline alert for `2026-10-13` (3 days remaining), while the serial result stayed `uncertain — please check`; portal automation stayed false and no external action ran. See `evidence/ventures/warranty/dry-run-result.json`. The screenshot capture is still pending.

Brand portal automation, homeowner emails, marketplace listing, and payment are not enabled or performed. Owner update on 2026-10-10: the Jobber test app is connected, but this fixture run did not verify complete live intake. The shared deadline tracker and document reader are not integrated into this venture's intake, and the Jobber read-only client does not expose all fields needed for full install intake. This checkpoint must remain unverified until those dependencies are available, screenshot evidence is saved, and a separate evaluator reviews the acceptance output and required real/sandbox checks.
