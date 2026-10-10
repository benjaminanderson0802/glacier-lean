# Mail block release check

From the repository root, run flock /tmp/glacier-heavy.lock .venv/bin/python -m unittest ventures.blocks.mail.tests.test_mail_acceptance -v.

The check proves render-only PDF and HTML output with no key, test-key-only API configuration, address-verification uncertainty when no key is present, sender and anti-impersonation checks, do-not-mail suppression, and separate landing pages containing each source record's distinct values. The Lob API test path is optional and only uses a test_ key.
