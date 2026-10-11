# Owner steps

Complete these one-time steps before the scheduled runs. The YouTube credentials stay under `CLIP_HOME`; with the default Windows setup, `CLIP_HOME` is `$env:USERPROFILE\.glacier\ventures\whop-clipping`.

## 1. Publish the site privacy page

Run the andersoneducation.us site publish command. It publishes the privacy page Google requires for the OAuth app.

## 2. Publish the Google OAuth app

Open [Google Auth Platform — Audience](https://console.cloud.google.com/auth/audience?project=anderson-education) and click **Publish app**. The app branding is already filled in.

## 3. Create the desktop OAuth client and authorize channels

In Google Auth Platform, open **Clients** → **Create client**. Choose **Desktop app**, name it **Glacier Clipping**, create it, and download its JSON. Then run these lines in PowerShell from the Glacier repository root. The copy command expects one downloaded `client_secret*.json` file; it saves the JSON to the default `CLIP_HOME\tokens\client_secret.json`.

```powershell
Set-Location $env:USERPROFILE\w\glacier-lean
New-Item -ItemType Directory -Force $env:USERPROFILE\.glacier\ventures\whop-clipping\tokens
Copy-Item $env:USERPROFILE\Downloads\client_secret*.json $env:USERPROFILE\.glacier\ventures\whop-clipping\tokens\client_secret.json
& $env:USERPROFILE\w\glacier-lean\.venv\Scripts\python.exe ventures\whop-clipping\scripts\authorize_channels.py
```

In the Google account chooser, select each linked channel in turn and confirm the helper identifies the expected handle before it saves that channel's token:

`@frameandmomentdesk`, `@highlightdesknotes`, `@replaynotesdesk`, `@quickreplaydesk`, `@dailycutnotes`, `@clipcurrentdesk`, `@sceneselectnotes`, `@momentarchivedesk`, `@thecliproomnotes`, and `@contextclipsdesk`.

Tokens stay in `CLIP_HOME\tokens\`. Never commit the downloaded client JSON or generated channel tokens.

## 4. Join campaigns you want to use

For source media, Producer first uses links exposed on the logged-out campaign detail page, then YouTube links named in the campaign rules or description. If neither exposes the approved videos, create CLIP_HOME\campaign_sources\{campaign-uuid}.txt and paste one approved public source URL per line. Producer records whether each source came from the public detail page, campaign rules, or this override in its local event ledger. Keep sources within the campaign's stated permissions and restrictions.

Check the Producer's `join_suggestions` in the status report. For a campaign you want to use, open its public URL, sign in and join it yourself in Content Rewards. Then paste that campaign URL on its own line in `CLIP_HOME\joined_campaigns.txt`. Do not enter campaign details in the config: Producer reads available rules, platform limits, CPM, budget, and source links from the public campaign pages. Only URLs in this file are eligible for Producer ranking. Joining and Whop account actions remain manual.

The scout fetches only logged-out public HTML on `contentrewards.com`, caches each URL for an hour, identifies itself as Glacier with the owner's contact email, and never calls `/api/` or accesses Whop pages/endpoints. See [the terms research](docs/WHOP.md).

## 5. Submit queued clips on Whop

Open `CLIP_HOME\submit-queue.html`, submit each queued clip on Whop, check it done, and download `submit-queue-done.json` to `CLIP_HOME`. The next Distributor status read reconciles the completed rows. Whop is a manual submit queue only until Whop grants written consent or publishes an official Content Rewards API. The owner sent Whop an email asking for written consent on 2026-10-11; no automated Whop access is enabled while awaiting a response.

Before enabling YouTube uploads, review and approve the campaign IDs in the private config, confirm the selected channel tokens, and set `live` to `true`. The default remains `false`; Whop submission stays manual regardless of YouTube live mode.
