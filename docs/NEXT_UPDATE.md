# Next update

Running list of bugs and fixes waiting for the next big update. Each merged fix adds a line here; when the owner says go, this becomes the release notes shown in Settings > About, and the list starts over.

Owner shorthand: a message starting with "+" means "add this change to the next update" (it is built and fixed as usual, listed here, and ships with the next big update).

Installed on the owner's PC: 0.2.0 (2026-10-08), release notes in docs/releases/v0.2.0.md.

## New

## Fixed

## Waiting to merge

## Owner's list for the next update

## Found while installing 0.2.0 (fix next)
- The review install script finds the engine by a fixed port; Glacier picks a new port each start, so its smoke table shows FAIL even when everything works (read the port from backend.log instead).
- Some status text still says "Ask" (for example "Ask is using Codex"); it should say "Build".
- Windows Smart App Control blocks unsigned builds; the owner turned it off on his PC. Code signing is needed before other people install Glacier.

## Release plan (owner decision 2026-10-08)
- Auto-update ships with the next big update: that release (v0.2.0) is the first with the updater, so it is installed once by hand.
- The release after it is the auto-update proof: the installed Glacier should offer it in Settings > About and install it on click. NORTHSTAR PH8.1 is recorded done after that.
- Fixes are collected here between releases, not shipped one by one.
