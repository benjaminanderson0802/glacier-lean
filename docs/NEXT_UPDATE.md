# Next update

Running list of bugs and fixes waiting for the next big update. Each merged fix adds a line here; when the owner says go, this becomes the release notes shown in Settings > About, and the list starts over.

Owner shorthand: a message starting with "+" means "add this change to the next update" (it is built and fixed as usual, listed here, and ships with the next big update).

Installed on the owner's PC today: the build from the Windows start-up fixes (2026-10-08), with hand-applied tool-check fixes.

## New
- Updates: Glacier can check for and install new versions from Settings > About (only after you click Install); a small notice on Home when one is ready.
- Flows can start when a new file appears in a folder or when a web request arrives; Automations shows how each flow starts.
- New step: Call a web API (saved secrets by name only, allowed sites, response shown in the run view).
- Spanish: every screen in Spanish, chosen in Settings > General.
- Ask remembers the conversation for follow-up questions.
- granite3.3:2b is the default local model everywhere.

## Fixed
- Windows: the tool check no longer hangs on a broken ollama.exe link (a winget download left as a zip); Ollama is found through its own local service.
- Windows: Glacier no longer starts npm's extensionless scripts (the "Unsupported 16-bit application" box).
- Windows: saving notes works when the data folder has a short 8.3 name or is on another drive.
- Runs finish right after their last step even when the computer is busy.
- Faster saves (fewer disk syncs), most noticeable on Windows.
- A claim's "ran the flow again" note can no longer be lost when the automatic research writes at the same time; worker output is no longer pasted into claims.
- A step run directly (sandbox checks) no longer fails when no run record exists yet.

## Waiting to merge (will be listed above once merged)
- Every action that changes something is recorded in the audit log.
- Memory can be restored from git after a full reinstall (proof script).
- Opening Glacier twice focuses the open window instead of starting a second one.
- The engine token no longer appears in backend.log.
- Notes written by hand no longer get an empty run_id line.
- Windows: no terminal window opens when Glacier starts.
- Ask uses Codex when Codex is signed in (Windows sign-in check fixed).
- Get started only picks a local model that is installed; Ask says plainly when a model is missing instead of failing.
- Ask's local model knows it is Glacier's assistant.
- Glacier starts even if its settings file was saved by Windows PowerShell (BOM).

## Owner's list for the next update (2026-10-08)
- Delete buttons on every page that lists something the owner made (flows, runs, notes, claims, conversations, secrets, files).
- Remove quotes and motivational text nobody asked for.
- Remove the pixel character from every page (owner decision).
- New look: three mockups of Home first; the owner picks one, then it is applied everywhere (fonts for "Glacier", page titles and body included).
- Memory map with real physics: linked notes pull together, others push apart, drag and pin, zoom and pan.
- Automations canvas: snap to grid, auto-layout, cleaner edges, no overlapping steps, minimap; templates show a real picture of the flow before you use them.
- Ask knows Glacier on every engine: what Glacier is, how to use its screens, your previous chats (when enabled), the current system state and your memory, personalised to you, whichever model or API answers.
- Window buttons (minimise and close) work, or Glacier uses the normal Windows title bar.
- Ask runs on your subscription command-line tool by default (Codex), with an easy switch to an API (OpenAI-compatible and Anthropic, owner decision) or a local model.

## Release plan (owner decision 2026-10-08)
- Auto-update ships with the next big update: that release (v0.2.0) is the first with the updater, so it is installed once by hand.
- The release after it is the auto-update proof: the installed Glacier should offer it in Settings > About and install it on click. NORTHSTAR PH8.1 is recorded done after that.
- Fixes are collected here between releases, not shipped one by one.
