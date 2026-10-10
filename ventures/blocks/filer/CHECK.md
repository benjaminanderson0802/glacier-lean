# Portal filer release check

From the repository root, run flock /tmp/glacier-heavy.lock .venv/bin/python -m unittest ventures.blocks.filer.tests.test_filer_acceptance -v.

The check starts a local mock portal with login, two data-entry steps, a review page, and a confirmation page. It proves that prepare fills the form and takes a screenshot without submitting, submit requires an approval id, successful submission saves a confirmation screenshot and PDF, and replaying the same idempotency key does not create a second filing. Only the local mock is exercised; real portal runs require a customer-authorized domain, credentials and approval.
