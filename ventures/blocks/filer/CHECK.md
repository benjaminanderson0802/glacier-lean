# Portal filer release check

From the repository root, run flock /tmp/glacier-heavy.lock .venv/bin/python -m unittest ventures.blocks.filer.tests.test_filer_acceptance -v.

The check starts a local mock portal with login, two data-entry steps, a review page, and a confirmation page. It proves that prepare fills the form and takes a screenshot without submitting, submit requires an approval id, successful submission saves a confirmation screenshot and PDF, and replaying the same idempotency key does not create a second filing. Only the local mock is exercised; real portal runs require a customer-authorized domain, credentials and approval.

Latest release check (2026-10-10): `heavy .venv/bin/python -m unittest ventures.blocks.filer.tests.test_filer_acceptance -v` — **3 tests passed**. Suite check: `heavy .venv/bin/python -m pytest -q ventures/blocks/filer/tests` — **3 passed in 2.87s**. The audit's earlier login-button timeout did not reproduce in the baseline rerun (3 passed in 2.94s); the runner now waits for the visible button in the login form and allows 20 seconds for the action.
