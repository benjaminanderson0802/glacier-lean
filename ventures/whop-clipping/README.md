# Whop Content Rewards clipping

This venture uses two Glacier automations. **Producer** reads Content Rewards' logged-out public campaign pages, stores a structured requirements checklist for campaigns the owner has joined, fetches their public sources, makes neutral clip masters, runs campaign QA, and stocks `CLIP_HOME/library/`. **Distributor** runs hourly, reserves each ready segment for one channel, observes that channel's deadline and posting limits, uploads to YouTube, then queues a manual Content Rewards submission. A channel never scouts or selects its own content.

`PublicDiscoverScout` only fetches public HTML from `contentrewards.com`, at most once per URL per hour. It obeys the site's robots.txt, never calls `/api/`, and identifies Glacier and `ben@andersoneducation.us` in its User-Agent. It does not access Whop pages, log in, or join campaigns. The owner joins campaigns manually, then pastes each URL on its own line in `CLIP_HOME/joined_campaigns.txt`; only those campaigns are eligible for Producer ranking. The latest high-value unjoined YouTube campaigns appear in the status report as “join these” suggestions. Whop's public API does not document Content Rewards campaigns or submissions. Distributor always uses the local manual queue and ignores automated submitter plugins. It creates `CLIP_HOME/submit-queue.html`, grouped by campaign, with the channel, Shorts URL, required caption/tags, and a done checkbox. Download the checked list as `submit-queue-done.json`, place it in `CLIP_HOME/`, and the next status read reconciles those rows. Submissions stay manual unless written consent or an official Content Rewards API is available; see [the terms research](docs/WHOP.md).

## Runtime and limits

- Producer keeps a target stock of at least 20 QA-passing clips. Failures are logged with reasons and never become ready library items.
- Distributor serves channels closest to their `last_post + 6h` deadline and targets at least one post per active channel in each 6-hour window when approved clips are available. It posts at most 6 clips per channel per day, keeps at least 2 hours between posts, never schedules beyond 6 hours, and stays below YouTube's 100/day upload quota.
- Paused channels are excluded and shown in status. It never reposts a clip. An at-risk deadline creates a ledger event and sends a Glacier notification when a notification URL is configured.
- Captions use word timings from faster-whisper and ASS rendered with ffmpeg/libass. The library stores a neutral master; Distributor burns the chosen channel's fixed base/highlight colors once its channel reservation is made. This avoids rendering ten channel variants for every clip. No-edit campaign media is copied byte-for-byte.
- The configured channel list and posting state are in the private `CLIP_HOME` config and ledger. Credentials, sources, media, and logs remain outside the repository.

## Run and check status

Copy `config.example.json` to `CLIP_HOME/config.json`, create `CLIP_HOME/joined_campaigns.txt` for campaign URLs you have manually joined, import both JSON flows into Glacier, and complete the setup steps in [OWNER-STEPS.md](OWNER-STEPS.md). Live YouTube uploads require `live: true`; the joined URL file is the campaign-specific owner gate. The exact Windows PowerShell setup commands are in that guide.

```sh
cd ventures/whop-clipping
~/w/glacier-lean/.venv/bin/python -m scripts.producer
~/w/glacier-lean/.venv/bin/python -m scripts.distributor --status
```

For a one-time manual run of both automations, use `python -m scripts.cycle` from this directory. Glacier schedules Producer and Distributor independently; Distributor's flow runs hourly.

The project uses pinned open-source `yt-dlp`, `gdown`, `faster-whisper`, and ffmpeg/libass. Whop browser automation is not included. Tests are in `tests/`; run them with:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests
```
