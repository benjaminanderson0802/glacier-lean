# Owner steps

## 1. Set up Google Cloud OAuth and authorize the YouTube channels

1. Open [Google Cloud Console](https://console.cloud.google.com/), sign in, and click **Select a project** → **New Project**. Enter a project name and click **Create**.
2. Select the new project. Open **APIs & Services** → **Library**, search **YouTube Data API v3**, open it, and click **Enable**.
3. Open **Google Auth Platform** → **Get started**. Enter the app name and support email. Choose **External**, add your email as a test user, then open **Audience** and click **Publish app** to move to Production. Google may show an unverified-app warning because this is personal use; that warning is expected.
4. Open **Clients** → **Create client**. Choose **Desktop app**, enter a name, and click **Create**. Click **Download JSON** and save the file as `client_secret.json` in the runtime token directory.
5. In PowerShell, run:

   ```powershell
   New-Item -ItemType Directory -Force $env:USERPROFILE\.glacier\ventures\whop-clipping\tokens
   Move-Item $env:USERPROFILE\Downloads\client_secret*.json $env:USERPROFILE\.glacier\ventures\whop-clipping\tokens\client_secret.json
   ~/w/glacier-lean/.venv/bin/python ventures/whop-clipping/scripts/authorize_channels.py
   ```

6. The authorization helper opens Google sign-in. Choose the first linked channel, review the requested YouTube permissions, and click **Allow**. Repeat once for each of these ten channels when prompted: `@frameandmomentdesk`, `@highlightdesknotes`, `@replaynotesdesk`, `@quickreplaydesk`, `@dailycutnotes`, `@clipcurrentdesk`, `@sceneselectnotes`, `@momentarchivedesk`, `@thecliproomnotes`, and `@contextclipsdesk`. Tokens stay under `CLIP_HOME/tokens/`.

## 2. Sign in to Whop once

1. In PowerShell, run:

   ```powershell
   ~/w/glacier-lean/.venv/bin/python ventures/whop-clipping/scripts/whop_login.py
   ```

2. In the opened browser, sign in to the owner's Whop account and complete any requested verification. Close the browser after the helper confirms the session is saved. The browser profile stays under `CLIP_HOME/browser-profile/`.
3. Still within this setup step, prepare the private runtime config in PowerShell:

   ```powershell
   New-Item -ItemType Directory -Force $env:USERPROFILE\.glacier\ventures\whop-clipping
   Copy-Item ventures/whop-clipping/config.example.json $env:USERPROFILE\.glacier\ventures\whop-clipping\config.json
   notepad $env:USERPROFILE\.glacier\ventures\whop-clipping\config.json
   ```

   Keep `live` set to `false` until ready. When enabling automation, enter only the campaign IDs Benjamin approved and change `live` to `true`. This private config, OAuth tokens, and browser profile stay outside the repository.
