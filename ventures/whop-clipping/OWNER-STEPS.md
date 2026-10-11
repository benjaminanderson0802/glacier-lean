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

## 4. Submit queued clips on Whop

Open `CLIP_HOME\submit-queue.html`, submit each queued clip on Whop, check it done, and download `submit-queue-done.json` to `CLIP_HOME`. The next Distributor status read reconciles the completed rows. Whop is a manual submit queue only until Whop grants written consent or publishes an official Content Rewards API. The owner sent Whop an email asking for written consent on 2026-10-11; no automated Whop access is enabled while awaiting a response.

Before enabling YouTube uploads, review and approve the campaign IDs in the private config, confirm the selected channel tokens, and set `live` to `true`. The default remains `false`; Whop submission stays manual regardless of YouTube live mode.
