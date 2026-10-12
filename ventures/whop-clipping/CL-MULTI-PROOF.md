# CL-MULTI implementation and verification

## Drift check and acceptance

- **Checkpoint:** PH12.22, venture integration and audit. This card is owner-authorized; PH5/PH9 remain in progress, so no North Star checkpoint status is changed here.
- **Defining properties and measures:** P-LOOPS / M-SURVIVE for multi-campaign production, P-CONTROL / M-INTERVENE for human requirements and pre-approval gating.
- **Existing tools:** reuse pinned `yt-dlp` and `gdown`; use the standard library for Dropbox downloads/ZIP extraction, WeTransfer public-link resolution, local cache management, and Windows scheduling glue.
- **Acceptance written first:** fixture coverage verifies repo briefs and private overrides; campaign ineligibility; CPM × budget allocation with at least one clip per campaign; source provider routing and LRU limits; immediate ready-library insertion; source-moment uniqueness; owner actions and pre-approval blocking; Windows task configuration. An opt-in public-network smoke covers Drive and Dropbox.

## Implemented

- Registry briefs load from `campaigns/<uuid>/`; matching `CLIP_HOME/campaigns/<uuid>/` briefs override them, and legacy `campaign_rules/<uuid>.txt` / `campaign_sources/<uuid>.txt` files take precedence where present.
- Ineligible campaigns are skipped with a `campaign_ineligible` event. Production consumes candidates one at a time, adds each QA-passing clip to the ready library immediately, and stops at the campaign's weighted daily share. The default daily goal is 40 clips, with a minimum allocation of one per eligible campaign.
- Drive files and folders use pinned `gdown`; Dropbox shared files and folders use `dl=1` and safe ZIP extraction; WeTransfer public links resolve through the public download flow, cache the file, and persist expiry metadata. Source cache eviction is LRU with a default 40 GB cap.
- Human-only requirements appear as per-campaign `owner_actions`. A draft requiring pre-approval is held out of public distribution.
- Added current-user hourly Windows runner and installer. The installer sets `live` true only with `-Live`; without it, `live` is false. No Whop submission automation was added.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pip install -r ventures/whop-clipping/requirements.txt` — completed; pinned requirements were already installed.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/whop-clipping/tests/test_multi_campaigns.py ventures/whop-clipping/tests/test_pipeline.py ventures/whop-clipping/tests/test_schedule.py` — **40 passed, 3 skipped**.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/whop-clipping/tests` — at that full-suite run, **76 passed, 3 skipped, 1 failed**. The failure is the existing `test_resumable_upload_sets_short_metadata_and_records_post`: the uploader stamps UTC while the ledger's default daily count uses local `date.today()`. The focused test reproduced the same failure once. This card did not modify that uploader, ledger counting behavior, or its test.
- Public network smoke: one Drive public file downloaded and passed its assertion. Dropbox returned `Content-Length: 10539499`; the smoke's then-current 5 MB cap refused it before transfer. The optional smoke test now defaults to 50 MB for the next run. The Dropbox live download is **not verified** in this card. PowerShell was unavailable in this Linux worktree, so the Windows scripts received fixture/static checks only.
- No WeTransfer network smoke was requested; fixture coverage verifies cached expiry metadata.

## Go-live command

From the repository root, after the owner completes the one-time channel authorization and private config setup, paste:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ventures\whop-clipping\scripts\install_schedule.ps1 -Live -Python "$env:USERPROFILE\w\glacier-lean\.venv\Scripts\python.exe"
```

This registers the hourly task and enables YouTube uploads. Whop submissions remain in the local manual queue.
