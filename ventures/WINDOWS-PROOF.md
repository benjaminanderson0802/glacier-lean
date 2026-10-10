# PH12.22 Windows proof (W1)

Date: 2026-10-10
Machine: Windows 11, from-source checkout `C:\Users\benja\glacier-dev`, branch `glacier-dev`
Commit: `07fdfe2 Fix venture dry runs on Windows`

## Failures and fixes

- The first installer run failed in `bind_command` with `re.PatternError: bad escape \U`. `re.sub` interpreted the quoted Windows Python executable as a replacement template. Python replacement now uses a callback. Runtime interpreter paths are quoted forward-slash drive paths, and `PYTHONPATH` uses the host separator (`;` on Windows) while retaining an inherited value with a quoted shell separator.
- Windows resolved `bash.exe` to `C:\Windows\System32\bash.exe` (the WSL launcher), which failed because no WSL distribution was available. Glacier now prefers the installed Git for Windows Bash and ignores that WSL alias. A generated venture command successfully ran through Git Bash and imported `ventures.blocks`.
- The first disposable live dry-run pass had missing synthetic intake files for Carpenter, CPSC, DIBBS, FDA, Freight, Property Tax, and Recall. These inputs were staged only in the disposable home from checked-in examples/tests (or clearly labeled synthetic records); no owner files were seeded. One first CPSC test input had an empty product list and was replaced with a non-empty example batch.
- FDA’s unconfigured Shopify connector correctly returned `setup_required` without reading product data, but the CLI returned exit 1, which marked the command node failed. The CLI now returns success for that expected setup state so Glacier reaches its explicit owner step. The no-connection regression test passes.
- `tesseract.exe` was not found on PATH. The main flow smoke tests still reached their intended stops; this does not establish image-OCR or venture release readiness. No Playwright browser was installed because this card’s acceptance was the live backend/API flow check, not a browser E2E board. No account, password, message, filing, listing, or payment action was performed.

## Windows code tests

Commands and results on this Windows PC:

```powershell
.venv\Scripts\python.exe -m pytest -q ventures/tests/test_windows_installer.py ventures/tests/test_install_idempotent.py ventures/tests/test_install_all.py -k "not discovery_is_data_driven_and_only_filters_by_slug"
# 7 passed, 1 deselected (the pre-existing discovery test is documented as stale in ventures/AUDIT-final.md)

.venv\Scripts\python.exe -m pytest -q ventures/fda-cosmetics/tests/test_fda_cosmetics.py
# 8 passed

Push-Location glacier\backend
..\..\.venv\Scripts\python.exe -m pytest -q tests/test_shell_commands.py
Pop-Location
# 4 passed

.venv\Scripts\python.exe -m compileall -q ventures\install_all.py glacier\backend\shell_commands.py ventures\tests\test_windows_installer.py glacier\backend\tests\test_shell_commands.py
# exit 0
```

The Windows installer tests simulate Windows interpreter paths and `;` while remaining platform-neutral for Linux. `git diff --check` passed before commit.

## Disposable live Glacier

The owner instance stayed on ports 8766/5176 and its data home was not used for this check. I launched `glacier/web/scripts/live.mjs` with:

```powershell
$env:GLACIER_HOME = "$env:TEMP\glacier-ph12-22-windows-proof-20261010"
$env:GLACIER_API_PORT = '8790'
$env:GLACIER_UI_PORT = '5190'
$env:GLACIER_PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
node glacier\web\scripts\live.mjs
```

Installer command, run twice against the disposable backend:

```powershell
$env:GLACIER_HOME = "$env:TEMP\glacier-ph12-22-windows-proof-20261010"
.venv\Scripts\python.exe ventures\install_all.py --api http://127.0.0.1:8790
```

After the final command-path update, the first refresh registered 31 flows (28 saved and 3 already unchanged); the next pass reported all 31 unchanged. An earlier clean pair reported 31 saved, then 31 unchanged. Both UI and API returned HTTP 200.

Dry-run API call used for each venture:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8790/api/ventures/$slug/run" `
  -Method Post -Headers $headers -ContentType 'application/json' -Body '{"dry_run":true}'
```

Final disposable run IDs and states (all 11 settled, zero failed nodes):

| Venture | Run | Result |
| --- | --- | --- |
| Apify tools | `a126ca7806f3` | done |
| Carpenter goods | `74dfc3dd9be7` | waiting at `approve_listing` |
| Co-op postcards | `07502568956e` | waiting at `mail_approval` |
| CPSC prep | `804f4da4912d` | waiting at `review-certify` |
| DIBBS supply | `7963a094de57` | waiting at `owner_review` |
| FDA cosmetics | `6179b9589170` | waiting at `customer_submit` |
| Freight claims | `26b8567b28b8` | waiting at `approve_customer_submission` |
| Property tax | `aa68fa41fda4` | waiting at `review_packet` |
| Recall checker | `ec2af2eb394e` | waiting at `review_results` |
| Utility audits | `8e93a64993f8` | waiting at `confirm_state` |
| Warranty | `40f452b2f567` | waiting at `review_draft` |

The first unseeded attempt and the first empty CPSC fixture produced failures; those run records were left intact. After staging synthetic inputs in the disposable home and correcting the FDA setup exit status, the final 11 runs above reached a normal completion or the intended owner stop. No synthetic inputs were copied to the owner’s data home.

## Owner dev Glacier install

The backend had loaded `glacier/backend/shell_commands.py`, so it was restarted with the supplied run script after verifying each stopped engine/UI process had `glacier-dev` in its command line. Stopped PIDs: 7420, 19320, 20996. Restart:

```powershell
Start-Process -FilePath powershell.exe `
  -ArgumentList @('-ExecutionPolicy','Bypass','-File','C:\Users\benja\glacier-dev-run.ps1') `
  -WindowStyle Hidden
```

The owner API and UI returned HTTP 200 after restart. Install command, run twice with the requested home:

```powershell
$env:GLACIER_HOME = "$env:USERPROFILE\.glacier-dev"
.venv\Scripts\python.exe ventures\install_all.py --api http://127.0.0.1:8766
```

Results: first pass exit 0, 31 flows saved across 11 ventures; second pass exit 0, 31 flows unchanged. API confirmation after the second pass:

- `GET /api/ventures`: 11 ventures.
- `GET /api/environments`: 31 flows.
- Flow definitions: 12 schedule nodes; 9 ventures report a next schedule time.
- `GET /api/home`: 33 `venture_steps` of kind `your_step`, covering all 11 ventures (3 steps each). The Home `needs_you` preview contains 20 due to its API display limit.

PH12.22 remains in progress; this Windows proof does not mark the checkpoint done or change NORTHSTAR status.