# Go live on the owner’s Windows PC

Complete the one-time setup in [OWNER-STEPS.md](OWNER-STEPS.md) first. In particular, create `CLIP_HOME\config.json`, authorize and verify the selected YouTube channels, add only campaigns the owner joined, and review the live upload settings. This command registers the hourly current-user task and sets `live` to `true`; YouTube uploads can begin on its first run. Whop Content Rewards submissions remain a manual local queue.

From any PowerShell prompt, paste this single line:

```powershell
Set-Location 'C:\Users\benja\gl-recall-apify'; $env:CLIP_HOME = Join-Path $env:USERPROFILE '.glacier\ventures\whop-clipping'; & '.\ventures\whop-clipping\scripts\install_schedule.ps1' -Live -Python 'C:\Users\benja\glacier-dev\.venv\Scripts\python.exe' -ClipHome $env:CLIP_HOME
```

To pause distribution immediately, create the `HOLD` file in the private clip home:

```powershell
New-Item -ItemType File -Force -Path (Join-Path $env:USERPROFILE '.glacier\ventures\whop-clipping\HOLD')
```

The Distributor checks `HOLD` at startup and again just before upload. Remove the file to resume:

```powershell
Remove-Item -Force -Path (Join-Path $env:USERPROFILE '.glacier\ventures\whop-clipping\HOLD')
```

The scheduled task can also be disabled from Windows Task Scheduler. Its daily log is written to `CLIP_HOME\logs\`.
