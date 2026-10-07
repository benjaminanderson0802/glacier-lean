# Integration health checks

The health check runs weekly on Monday at 06:17 UTC and can also be started from the Actions tab. It creates a temporary Python environment from `setup/requirements.txt`, then runs the backend tests, importer/template/benchmark/tool suites, and the verification benchmark. The benchmark must keep false-done below 2% and verified-good runs at or above 98%.

The security section runs the prompt-injection suite and passes only when that suite reports success (all attack cases blocked). If the suite is missing, the report says so and the overall check fails. No security result is inferred from the other test suites.

Run `python setup/health_check.py` for the clean environment used in CI. Run `python setup/health_check.py --quick` to reuse the current Python environment while developing. Both modes write `health-report.json` in the repository root; `--report PATH` selects another location.

The report contains the date, Python version, an overall `passed` value, and a `sections` list. Each section has a plain-language name, a `passed` value, and a short summary. A failed section makes the process exit with status 1. The report also lists pinned packages with newer versions seen on PyPI under `proposals`; these are suggestions only. The script never edits requirements files or installs upgrades from those proposals.

In GitHub Actions, download the `glacier-health-report` artifact to inspect the same JSON report after a run.
