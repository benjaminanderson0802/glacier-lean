# Whop Content Rewards clipping

This venture uses two Glacier automations. **Producer** loads the campaign briefs in `campaigns/<uuid>/` (`summary.json`, `rules.txt`, and `sources.txt`), with matching private `CLIP_HOME/campaigns/<uuid>/` files taking precedence. It fetches campaign sources, makes neutral bases and captioned previews, runs media and campaign QA, and stocks each passing clip immediately in `CLIP_HOME/library/`. **Distributor** runs hourly, reserves each ready segment for one channel, observes that channel's deadline and posting limits, uploads to YouTube, then queues a manual Content Rewards submission. A channel never scouts or selects its own content.

`PublicDiscoverScout` only fetches public HTML from `contentrewards.com`, at most once per URL per hour. It obeys the site's robots.txt, never calls `/api/`, and identifies Glacier and `ben@andersoneducation.us` in its User-Agent. It does not access Whop pages, log in, or join campaigns. The owner joins campaigns manually, then pastes each URL on its own line in `CLIP_HOME/joined_campaigns.txt`; only those campaigns are eligible for Producer ranking. The latest high-value unjoined YouTube campaigns appear in the status report as “join these” suggestions. Whop's public API does not document Content Rewards campaigns or submissions. Distributor always uses the local manual queue and ignores automated submitter plugins. It creates `CLIP_HOME/submit-queue.html`, grouped by campaign, with the channel, Shorts URL, required caption/tags, and a done checkbox. Download the checked list as `submit-queue-done.json`, place it in `CLIP_HOME/`, and the next status read reconciles those rows. Submissions stay manual unless written consent or an official Content Rewards API is available; see [the terms research](docs/WHOP.md).

## Runtime and limits

- Producer keeps a target stock of at least 20 QA-passing clips. Failures are logged with reasons and never become ready library items.
- Producer targets 80 new ready clips each Pacific day by default (`daily_target`), allocated across eligible campaigns by `CPM × budget remaining × feedback factor`. Each campaign stops at its share or when distinct non-overlapping moments run out; an empty source cannot create extra stock to fill a quota. Source moments are planned before rendering, so shares are bounded by actual non-overlapping candidates; clips then render and enter stock one at a time. Source downloads use an LRU cache capped by `sources.max_source_gb` (default 40 GB); eligible source links include YouTube, public Google Drive files/folders, Dropbox files/folders, and public WeTransfer links.
- Campaigns marked `eligible_for_new_youtube_shorts_channels: false` are skipped with a status reason. Requirements needing a human appear under `owner_actions`; campaigns requiring draft pre-approval remain out of public upload until the campaign checklist is updated after approval.
- Distributor serves channels closest to their `last_post + 6h` deadline and targets at least one post per active channel in each 6-hour window when approved clips are available. The defaults are `per_channel_daily: 8`, `min_gap_minutes: 150`, and an even three-hour cadence (80 posts across ten channels). Missed deadlines never override the minimum gap. `youtube_daily_insert_quota: 100` gives an 85-attempt project ceiling, preserving a 15% margin. The atomic ledger reservation happens before sending an insert, counts failed attempts, and stops every channel until Pacific midnight when exhausted. All channels sharing the API project must share CLIP_HOME; reduce `global_daily_cap` if other applications use its upload bucket.
- Paused channels are excluded and shown in status. It never reposts a clip. An at-risk deadline creates a ledger event and sends a Glacier notification when a notification URL is configured.
- Captions use word timings from faster-whisper and ASS rendered with ffmpeg/libass. The library stores a passing captioned preview plus its neutral base; Distributor renders the chosen channel's fixed base/highlight colors from that base and rechecks the actual variant. This avoids rendering ten channel variants for every clip. No-edit media stays byte-for-byte; without an independently supplied neutral reference and timed captions it cannot satisfy the caption evidence gate and is rejected with a reason.
- The configured channel list and posting state are in the private `CLIP_HOME` config and ledger. Credentials, sources, media, and logs remain outside the repository.

## Run and check status

Copy `config.example.json` to `CLIP_HOME/config.json`, create `CLIP_HOME/joined_campaigns.txt` for campaign URLs you have manually joined, import both JSON flows into Glacier, and complete the setup steps in [OWNER-STEPS.md](OWNER-STEPS.md). Live YouTube uploads require `live: true`; the joined URL file is the campaign-specific owner gate. The exact Windows PowerShell setup commands are in that guide.

```sh
cd ventures/whop-clipping
~/w/glacier-lean/.venv/bin/python -m scripts.producer
~/w/glacier-lean/.venv/bin/python -m scripts.distributor --status
```

For a one-time manual run of both automations, use `python -m scripts.cycle` from this directory. Glacier schedules Producer and Distributor independently; Distributor's flow runs hourly.

On Windows, register the current-user hourly task from the repository root after setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ventures\whop-clipping\scripts\install_schedule.ps1 -Live -Python "$env:USERPROFILE\w\glacier-lean\.venv\Scripts\python.exe"
```

Omit `-Live` to keep uploads disabled. The task's combined output is appended under `CLIP_HOME/logs/`.

The project uses pinned open-source `yt-dlp`, `gdown`, `faster-whisper`, and ffmpeg/libass. Whop browser automation is not included. Tests are in `tests/`; run them with:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests
```

## Quality and owner review

The gate requires FFmpeg (with libass) and ffprobe and fails closed if media or evidence is missing. It measures black/frozen intervals on both output and neutral base, integrated loudness (default -18 to -14 LUFS), true peaks below -0.1 dBFS, opening silence, meaningful timed transcript words or visual motion in the first two seconds, real 1080×1920 dimensions and campaign duration. Caption frames must differ locally from the base at at least 80% of sampled word midpoints. It also checks public tags, brand spellings, banned transcript topics, all stocked/posted perceptual hashes and normalized transcripts, and source-time overlap across channels and campaigns. A six-bit dHash distance with 85% matching frames, or transcript similarity of at least 0.88, rejects a near-duplicate. Missing legacy duplicate evidence fails closed.

The local score weights hook strength (25), speech density (25), caption coverage (20), visual motion (15), and thought completeness (15). Completeness uses sentence-ending punctuation as a heuristic; the score does not establish semantic accuracy. `min_quality` defaults to 70. Every hard gate must also pass, regardless of score. Distributor selects the highest scores first, using campaign/channel diversity to break ties. No paid or remote model is called.

Open `CLIP_HOME/review/<Pacific-date>.html` for the posted/rejected thumbnail strips, public title and description, score components and rejection reasons. The page is rebuilt from ledger events; undecodable media has an explicit thumbnail-unavailable message. Create an empty `CLIP_HOME/HOLD` file to stop distribution, including a second check immediately before upload. Remove it to resume. Status reports expose the hold and remaining upload allowance.

`CLIP_HOME/whop_results.csv` is created with `clip_id,status,reason` headers. Fill in `accepted`, `approved`, `rejected` or `flagged` results from Whop. The last row for each known clip wins; duplicate rows do not multiply penalties. Campaign allocation is multiplied by `(accepted + 1) / (accepted + rejected + 1)`. Reasons appear under `whop_feedback` in status. Editing a result corrects the next allocation. Whop submission remains manual.

The older keys `daily_target_clips`, `daily_channel_cap`, and `min_spacing_hours` remain supported when their new equivalents are absent. Copy the new values into existing private configurations to opt into the owner's raised output. Existing old configuration files are not overwritten.

Media fixtures and scoring/scheduling regressions: `python -m pytest -q tests/test_quality.py`. Validation results and remaining independent-fixture work: [CL-QUALITY-PROOF.md](CL-QUALITY-PROOF.md).
