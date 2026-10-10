# Mail block release check

From the repository root, run flock /tmp/glacier-heavy.lock .venv/bin/python -m unittest ventures.blocks.mail.tests.test_mail_acceptance -v.

The check proves render-only PDF and HTML output with no key, test-key-only API configuration, address-verification uncertainty when no key is present, sender and anti-impersonation checks, do-not-mail suppression, and separate landing pages containing each source record's distinct values. The Lob API test path is optional, only uses a `test_` key, and requires an `approval_id`; otherwise the postcard remains render-only.

Latest release check (2026-10-10): `heavy .venv/bin/python -m unittest ventures.blocks.mail.tests.test_mail_acceptance -v` — **4 tests passed**. Suite check: `heavy .venv/bin/python -m pytest -q ventures/blocks/mail/tests` — **4 passed in 0.02s**.
