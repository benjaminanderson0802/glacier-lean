# Whop Content Rewards clipping

This venture uses two Glacier automations. **Producer** reviews locally supplied campaign records, stores a structured requirements checklist, fetches sources, makes neutral clip masters, runs campaign QA, and stocks `CLIP_HOME/library/`. **Distributor** runs hourly, reserves each ready segment for one channel, observes that channel's deadline and posting limits, uploads to YouTube, then queues a manual Whop submission. A channel never scouts or selects its own content.

Whop's Terms prohibit automated service access without written consent. The reviewed public API does not document Content Rewards campaigns or submissions. The default Scout reads `CLIP_HOME/campaigns.json`; it does not connect to Whop. The default `ManualQueueSubmitter` creates `CLIP_HOME/submit-queue.html`. It is grouped by campaign and shows the channel, Shorts URL with copy, required caption/tags, and a done checkbox. Download the checked list as `submit-queue-done.json`, place it in `CLIP_HOME/`, and the next status read reconciles those rows. The Submitter adapter remains replaceable if Whop grants written consent or ships an official API.

## Runtime and limits

- Producer keeps a target stock of at least 20 QA-passing clips. Failures are logged with reasons and never become ready library items.
- Distributor serves channels closest to their `last_post + 6h` deadline. It posts at most 6 clips per channel per day, keeps at least 2 hours between posts, never schedules beyond 6 hours, and stays under the 100/day YouTube quota.
- Paused channels are excluded and shown in status. It never reposts a clip. An at-risk deadline creates a ledger event and sends a Glacier notification when a notification URL is configured.
- Captions use word timings from faster-whisper and ASS rendered with ffmpeg/libass. The library stores a neutral master; Distributor burns the chosen channel's fixed base/highlight colors once its channel reservation is made. This avoids rendering ten channel variants for every clip. No-edit campaign media is copied byte-for-byte.
- The configured channel list and posting state are in the private `CLIP_HOME` config and ledger. Credentials, sources, media, and logs remain outside the repository.

## Run and check status

Copy `config.example.json` to `CLIP_HOME/config.json`, add owner-approved campaign records to `CLIP_HOME/campaigns.json`, import both JSON flows into Glacier, and complete YouTube OAuth setup using [OWNER-STEPS.md](OWNER-STEPS.md). Live YouTube uploads require `live: true` and explicit approved campaign IDs.

```sh
cd ventures/whop-clipping
~/w/glacier-lean/.venv/bin/python -m scripts.producer
~/w/glacier-lean/.venv/bin/python -m scripts.distributor --status
```

For a one-time manual run of both automations, use `python -m scripts.cycle` from this directory. Glacier schedules Producer and Distributor independently; Distributor's flow runs hourly.

The project uses pinned open-source `yt-dlp`, `gdown`, `faster-whisper`, and ffmpeg/libass. Whop browser automation is not included. Tests are in `tests/`; run them with:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_schedule.py
```
