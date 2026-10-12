# U-ROOM

Owner-approved final adjustments, Benjamin Anderson, 2026-10-10.

- Checkpoint: PH5.4 layout refinement; this card does not claim a phase exit.
- Dependencies: PH3 has an owner-approved exit; PH4 has implemented checkpoints but remains in progress. The explicit parallel-safe U-ROOM assignment authorizes this shell work.
- Properties and metrics: P-USABLE / M-TTFA and P-CONTROL / M-INTERVENE, by keeping navigation, live work and approvals reachable.
- I-01: reuse the installed React, CSS projective wall mapping, API client and Playwright. Custom work is UI glue, not a replacement engine. No new dependencies or paid services.
- Acceptance basis, before edits: existing shell.spec.mjs, messenger.spec.mjs, ask_context.spec.mjs, layout_overlap.spec.mjs, spanish.spec.mjs and live_real_backend.spec.mjs; TypeScript, theme lint, translation parity. Tester-owned checks remain untouched. Capture Chromium at 1280x800, 1440x900, 1920x1080 and 2560x1440 with the supplied room reference. Exercise real engine running/waiting/completed state and keyboard navigation. Builder screenshots and observations supplement independent acceptance; they do not replace it.

Initial observations: global arrows and Enter intercept screen controls; menu rows/padding can exceed the left panel at small sizes; left engine names are hard-coded; SideStatus only renders Messenger. Preserve the messenger and its test IDs while adding live status.

Environment note: the interrupted attempt recorded `tsc: not found`; pinned project dependencies are now available in this worktree and `npm run build` passes. The shared dependency target was not modified.

## Results

- `npm run build`, `npx tsc -b`, `node e2e/theme_lint.mjs`, `node scripts/check-i18n.mjs --fail`: pass.
- Room helper tests: 4/4 pass. The added approval helper covers waiting runs omitted from Home's capped needs-you list.
- `shell.spec.mjs`, `messenger.spec.mjs`, `ask_context.spec.mjs`, `layout_overlap.spec.mjs`, `spanish.spec.mjs`: pass.
- `live_real_backend.spec.mjs`: pass against a disposable real FastAPI engine; the real canvas run, Ask request, and messenger event path completed.
- `capture.mjs`: real engine run reached an approval, appeared in the right wall, and completed after approval. No active teams were present in the engine, so the live team section showed its empty state; no worker process was started.
- Chromium captures at 1280×800, 1440×900, 1920×1080, 2560×1440, plus running, completed and keyboard-focus states are saved alongside the reference. The observed menu focus moved from Home to Ask with ArrowDown and to Settings with End; the focus ring was visible. There were no page errors.
