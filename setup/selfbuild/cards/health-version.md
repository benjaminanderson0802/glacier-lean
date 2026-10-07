# Add a version option to the health check

Update `setup/health_check.py` so `--version` prints the app version from
`glacier/web/package.json` and exits with status 0. Add a test for `--version`
to the existing health check tests in `setup/test_health_check.py`.

Keep this change limited to the version option and its test. Do not change
checks, test configuration, verification rules, or other files.
