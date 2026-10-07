# Integration health checks

The health check runs weekly on Monday at 06:17 UTC and can also be started from the Actions tab. It creates a temporary Python environment from `setup/requirements.txt`, then runs the backend tests, importer/template/benchmark/tool suites, and the verification benchmark. The benchmark must keep false-done below 2% and verified-good runs at or above 98%.

The security section runs the prompt-injection suite and passes only when that suite reports success (all attack cases blocked). If the suite is missing, the report says so and the overall check fails. No security result is inferred from the other test suites.

Run `python setup/health_check.py` for the clean environment used in CI. Run `python setup/health_check.py --quick` to reuse the current Python environment while developing. Both modes write `setup/.health/health-report.json`, a git-ignored location; `--report PATH` selects another location. Every check subprocess has a 30-minute limit by default. Set `GLACIER_HEALTH_TIMEOUT_SECONDS` to change it.

The report contains the date, Python version, an overall `passed` value, and a `sections` list. Each section has a plain-language name, a `passed` value, and a short summary. A failed section makes the process exit with status 1. A subprocess that reaches its time limit is shown as `timed out`. The report also lists pinned packages with newer versions seen on PyPI under `proposals`; these are suggestions only. The script never edits requirements files or installs upgrades from those proposals. The network check has a 90-second total budget, and stops at the first network error with `Upgrade check skipped (no network)`.

In GitHub Actions, download the `glacier-health-report` artifact to inspect the same JSON report after a run. GitHub Actions cannot start jobs on this private repository while the account spending limit is $0. To get a local weekly run in the meantime, schedule it on a machine with the project checkout and dependencies.

Windows Task Scheduler command (run from the repository root; replace the interpreter path with the installed project interpreter):

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 07:00 /TN GlacierHealth /TR '"C:\path\to\python.exe" setup\health_check.py'
```

Linux cron line (runs Mondays at 06:17 UTC):

```cron
17 6 * * 1 cd /path/to/glacier-lean && /path/to/python setup/health_check.py >> setup/.health/weekly.log 2>&1
```
