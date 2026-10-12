# YouTube setup and operating rules

The YouTube adapter uses only Google's official YouTube Data API v3 through
`google-api-python-client` and OAuth through `google-auth-oauthlib`. It does not
automate the YouTube website, scrape YouTube, or buy or simulate engagement.
The ten configured handles are the owner's linked Whop Content Rewards
channels. Credentials, media, the SQLite ledger, and logs stay under `CLIP_HOME`
(default `~/.glacier/ventures/whop-clipping`).

## One-time authorization

1. In Google Cloud, create or select a project, enable YouTube Data API v3, and
   create an OAuth client of type **Desktop app**. Download its client JSON.
2. Put it at `CLIP_HOME/tokens/client_secret.json`. On Windows, the default is
   `%USERPROFILE%\.glacier\ventures\whop-clipping\tokens\client_secret.json`.
   Do not put this file or any generated token in the repository.
3. Run the script using the venture venv. On Windows PowerShell:

   ```powershell
   & "$env:USERPROFILE\w\glacier-lean\.venv\Scripts\python.exe" ventures\whop-clipping\scripts\authorize_channels.py
   ```

   On Linux:

   ```text
   ~/w/glacier-lean/.venv/bin/python ventures/whop-clipping/scripts/authorize_channels.py
   ```

   Google's installed-app flow opens a loopback consent page and asks for
   `youtube.upload` and `youtube.readonly`. In Google's account chooser,
   select the exact linked channel, including the appropriate Brand Account.
4. The script calls `channels.list(mine=true)` after consent, checks the returned
   channel handle against the handle it is authorizing, and only then writes
   `CLIP_HOME/tokens/@handle.json`. It repeats until all ten handles are done.
   If it reports the wrong selected channel, no token is saved for that handle;
   repeat consent and choose the correct channel.

The script prints channel names and authorization progress, never access or
refresh tokens. To replace a token, remove only that channel's JSON from the
private runtime directory and run the script again.

## Quota and upload behavior

Google's current [`videos.insert` reference](https://developers.google.com/youtube/v3/docs/videos/insert)
states that `videos.insert` has a quota cost of **1 unit** in the **Video Uploads**
bucket and a daily limit of **100 calls**. It also states that uploads from
unverified API projects are **not restricted to private viewing mode**. The
adapter records a quota reservation in the local event ledger before each
upload and defaults to a stricter project-wide cap of **85 upload attempts per day**;
the configured value is clamped to 85 (15% safety margin). The ledger keys its safety count to
Google's Pacific-time quota day. A `quotaExceeded` response records a stop event
and prevents further uploads for that day. Google controls the project's actual
quota window, so the API Console remains the authoritative usage display.

Uploads use resumable media requests with bounded exponential retries for 5xx
responses. A public upload is sent only when the private config has
`"live": true` and the caller is not in dry-run mode. A dry-run upload returns a
local placeholder `Post` and sends no upload request. The request sets the configured video
category (default `22`), clips titles to YouTube's 100-character limit, attaches
the campaign hashtags/disclosures assembled by the pipeline, sets
`selfDeclaredMadeForKids` to false, and includes `containsSyntheticMedia` when
the config or clip explicitly supplies that declaration. A successful post URL
is `https://youtube.com/shorts/<video-id>`.

## Account and campaign safeguards

- The pipeline assigns each segment to one channel and checks the local ledger
  for duplicate clips and any source-time overlap before upload. The adapter
  repeats the cross-channel overlap and already-posted checks at its boundary.
- The pipeline enforces the approved campaign list, allowed platform, required
  campaign tags and disclosure, length rules, and the no-edit passthrough rule.
  The uploader does not rewrite video bytes; it only constructs upload metadata.
- The default per-channel cap is eight uploads a day, with at least 150 minutes
  between posts and an even three-hour cadence. The project-wide cap is at most 85 attempts a day,
  leaving room below Google's 100-call daily upload limit.
- A 403 or a terms-, strike-, suspension-, or termination-like response pauses
  that channel in the ledger. Quota errors stop the project's uploads for the
  day. View monitoring pauses a channel when at least six posts are present in
  the latest 28 days and the 7-day median views fall below 20% of the median for
  the preceding 21 days.
- Never buy or automate views, likes, comments, or subscribers, and never use
  this adapter to disguise reused material or evade YouTube's systems.

## YouTube content policies

YouTube's [spam, deceptive practices, and scams policy](https://support.google.com/youtube/answer/2801973)
prohibits fake engagement, deceptive promotion, scraped reposts without added
value, and automated or synthetic mass production of repetitive content. The
[inauthentic content monetization policy](https://support.google.com/youtube/answer/1311392)
also says that mass-produced, repetitive, generic, or manipulative content may
not be eligible for monetization; reused-content rules still apply separately.
API access and a successful upload do not establish that a clip is authorized,
transformative, or eligible for monetization.

Use this workflow only for campaign sources the owner is authorized to use and
whose campaign rules permit the clip and YouTube posting. The pipeline adds the
campaign's required disclosure and tags, respects its allowed-platform and
editing instructions, assigns one non-overlapping segment to one channel, and
limits frequency. Those safeguards reduce operational mistakes; they do not
replace rights review or guarantee compliance or monetization. Do not flood the
ten channels with interchangeable clips. Pause and review source rights,
originality, and channel variation if the output would be repetitive or would
add no meaningful context or value for viewers.

## Local checks

The YouTube fixtures use `googleapiclient.http.HttpMockSequence`; they do not
contact Google. Run them with:

```text
~/w/glacier-lean/.venv/bin/python -m pytest -q \
  ventures/whop-clipping/tests/test_youtube_upload.py \
  ventures/whop-clipping/tests/test_youtube_channels.py
```
