# Whop Content Rewards clipping

This venture scouts Whop Content Rewards campaigns, fetches campaign source media, finds candidate short segments, applies required campaign disclosures, assigns each segment to one linked YouTube channel, uploads eligible Shorts, and submits their post URLs to Whop. It uses a local SQLite event ledger and keeps source media, clips, credentials, browser state, and logs under `CLIP_HOME` (default: `~/.glacier/ventures/whop-clipping`). No secrets or runtime media belong in the repository.

The pipeline is **dry-run by default**. To do a dry run, copy `config.example.json` to `CLIP_HOME/config.json` and run from the repository root:

```powershell
~/w/glacier-lean/.venv/bin/python ventures/whop-clipping/scripts/cycle.py --dry-run
```

For Linux, use the same Python module path for the project's virtual environment. The owner setup is click-by-click in [OWNER-STEPS.md](OWNER-STEPS.md). Live mode requires `live: true`, an explicitly approved campaign ID, and configured CL-YOUTUBE / CL-WHOP adapters:

```powershell
~/w/glacier-lean/.venv/bin/python ventures/whop-clipping/scripts/cycle.py --live
```

The default linked YouTube channel list is fixed in the sample configuration. The default limits are three uploads per channel per day, at least two hours between uploads to a channel, and a project cap of 90 uploads daily (below YouTube's 100/day quota). Live posts receive a randomized delay. Clips are assigned once, and the ledger rejects segments with more than 30% overlap against an existing allocation. Campaign rules determine disclosures and required tags. A campaign marked “no editing” is passed through byte-for-byte. A flagged Whop submission pauses that campaign on its channel; YouTube strike/terms errors and reported view collapse pause a channel. The pipeline never purchases or fabricates views, likes, comments, or subscribers.

`CLIP_HOME/ledger.db` contains campaign/source/clip/post/submission/pause/event tables and can be rebuilt from original campaign/source records. A copy of `ledger.db` is convenient for audit but is not the only copy of important source data: campaign links and source provenance are also retained in the event and source records.

The core uses open-source `yt-dlp`, `gdown`, `faster-whisper`, and `ffmpeg`; local Ollama scoring (`granite3.3:2b`) is optional and skipped when unavailable. Python package versions are pinned in [requirements.txt](requirements.txt); ffmpeg and ffprobe are external executables and are not bundled. The platform adapters are loaded by class name from `plugins` (`whop_scout.WhopScout`, `youtube_upload.YouTubeUploader`, `whop_submit.WhopSubmitter` by default); they are supplied by the CL-WHOP and CL-YOUTUBE cards. Missing adapters fail closed for live runs.

Tests are in `ventures/whop-clipping/tests/`; run them independently to avoid generic `scripts` import collisions with other venture suites:

```powershell
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/whop-clipping/tests
```
