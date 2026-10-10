# Card C2: final end-to-end proof

## Acceptance test (written before proof work)

On this machine's real Glacier backend and available real engines, complete the Build screen project proposal, one refinement, acceptance, visible node reveal, run, and Memory result check. Confirm screen context in Glacier's reply. Repeat a proposal with Codex CLI and local granite; repeat with an API engine only if this machine has an owner-configured key, monthly cap, model, and allowed host. Propose and review a UI change, approve it, and retain the unmerged branch only if its reported checks pass. In Messenger, open Codex, Claude, worker, and Glacier threads; send where enabled and observe replies. Save up to ten small screenshots under `evidence/ui/final-*.png`. Reproduce and resolve the reported assistant approval/run failure if it is real. Finally, run `npm run check:ui` and the full backend suite; record exact results and any skipped route.

## Drift check

- **Checkpoint:** PH5 assistant conversational control, especially PH5.1–PH5.3; this is final real-hardware acceptance evidence for the assistant→proposal→approved Environment path.
- **Dependencies:** PH3 and PH4 are listed as PH5 prerequisites. The requested base is `origin/glacier-final`, which includes the merged prerequisite cards. This proof does not mark a checkpoint done or change NORTHSTAR status.
- **Property / metric:** P-GOALS and P-CONTROL directly; P-MEMORY and P-PORTABLE through memory output and engine swaps; P-USABLE through real screen and messenger paths. M-VERIFIED, M-LOCAL, and M-COST are evidenced qualitatively for these runs, not treated as aggregate benchmark measurements.
- **Existing tool (I-01):** Glacier's existing assistant, Ollama, official Codex CLI, Playwright, and test boards cover the task. No new tool or paid service is added. An API route is used only when the owner's existing configuration is present.
- **Acceptance test:** The end-to-end conditions above, including screenshots and both full test boards. The targeted regression is first reproduced with `tests/test_assistant_chat_runs.py::test_approved_run_now_starts_one_and_lists_run_and_appends_result_once`.

## Results

The proof used the real backend started by `glacier/web/scripts/live.mjs` with a disposable profile at `/tmp/glacier-card-c2-proof-aicrPh`; Codex CLI 0.161.0 was signed in and Ollama 0.40.0 had `granite3.3:2b` installed. The captured request contained `screen: "automations/build"`; Glacier's opening response referred to Automations / New flow, and the generated proposal's saved context explicitly says the owner is on `automations/build`. The `final-01` screenshot preserves the screen-context chip and reply.

From Automations / Build, Glacier proposed the daily notes flow, then incorporated one refinement. The accepted nodes appeared on the canvas in this order: `schedule → read_notes → summarize → approval → save_summary → result`. The refined `read_notes` command read Markdown contents directly under `notes`; the Codex prompt included `{prev_output}` and the approval prompt was rendered literally without a token. The node reveal observer recorded all six nodes after acceptance. See `final-02` through `final-04`.

I seeded the flow workspace with a note stating that the neighborhood garden chose tomatoes and basil and meets again October 16. Run `3c95f2526584` reached `done`; after approving the gate, Codex produced “The neighborhood garden met Thursday and chose tomatoes and basil to grow. The next meeting is October 16.” The Memory API returned that text at `notes/morning-summary.md`, and I opened the note in the Memory screen. See `final-05` and `final-06`.

The proposal step was repeated with the local `granite3.3:2b` route; it returned a real proposal. The API engines were skipped because neither OpenAI-compatible nor Anthropic had complete owner configuration (saved secret, model, monthly cap, pricing, and allowed base address as applicable). The live engine list reported those missing settings; see `final-07`.

Messenger opened an imported Codex session and a fresh Codex thread replied “C2 Messenger proof passed.” Sending to the imported session returned HTTP 502; the fresh thread path succeeded. I filed [claim CLM-2026-10-09-C2-IMPORTED-CODEX-SEND](../vault/claims/2026-10-09-c2-imported-codex-send.md) rather than retrying the archived session. The real Claude history thread opened read-only because Claude CLI is not installed, so its composer was correctly unavailable. A pending worker thread accepted an owner note and displayed it; this worker-thread action records owner instructions and does not produce an agent reply. The Glacier thread replied “garden confirmed.” See `final-08` and `final-09`.

The UI-change requirement remains incomplete. The first real request returned a diff above the validator's 80,000-character ceiling, which the schema had not stated. I aligned the schema with the validator and added a focused-diff instruction. In a fresh conversation, the next real Codex request recorded `assistant.model_call` but did not return a proposal or terminal event within 180 seconds. I stopped within the card's two-attempt repair budget and filed [claim CLM-2026-10-09-C2-UI-CHANGE-LIVE-STALL](../vault/claims/2026-10-09-c2-ui-change-live-stall.md). No UI branch was approved or merged and no UI-change branch checks ran.

The reported regression `test_approved_run_now_starts_one_and_lists_run_and_appends_result_once` passes in the current worktree (one-test run and combined targeted runs); it was not reproducible as a failure. Full backend suite: `cd glacier/backend && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests` — **769 passed, 1 skipped, 5 warnings** in 674.63 seconds.

Full UI command: `cd glacier/web && npm run check:ui` — **failed at step 11/27, `e2e/every_control.spec.mjs`**. Steps 1–10 passed, including theme lint (51 files), sprite identity, i18n parity (819 keys), TypeScript, production build, and the preceding E2E specs. The failure recorded 91 click timeouts in the Messenger side panel. The control audit snapshots list buttons, clicks **New chat** (which intentionally switches Messenger from the thread list to the new-chat form), then tries the now-hidden thread rows without returning to the list; the same stale targets recur on each route. The Claims route also timed out on the form's Back button. `Messenger.tsx` renders either the list or the new-chat form for these mutually exclusive views. I did not edit the existing test that judges this behavior. Steps 12–27 did not run because the board exits on step 11 failure.

## Small bugs found and fixes

- The automation intent heuristic did not recognize “every morning”; it sent the request through ordinary chat instead of the flow planner. Added the phrase to the automation classifier and covered it with `test_assistant_chat_morning.py`.
- Planner instructions could propose reading file names instead of note contents, searching too broadly, mishandling POSIX shell syntax, or saving the wrong text. Clarified folder-scoped reads, Memory writes, valid checks, and workspace-relative command folders; added `test_assistant_planner_memory.py`.
- Prior output is interpolated into Codex prompts only through `{prev_output}`. The planner had only said the content was in the prior step. It now requires the token for command-to-AI handoffs and prohibits the token in literal approval prompts; the planner test covers both.
- A relative command `cwd` was resolved from the backend process directory instead of the flow workspace. It now resolves beneath the workspace; covered by `test_runner_workspace_defaults.py`.
- The Codex runner passed the UI label `default` as a literal model name, which the real Codex CLI rejected. It now omits `-m` for the default model; covered by `test_runner_workspace_defaults.py`.
- UI-change structured output omitted the validator's diff length bound, allowing an oversized model response to fail only after generation. Added the validator limit to the schema and requested focused diffs; covered by `test_assistant_ui_change_schema.py`. A separate live-call stall remains open in the claim above.
- One imported Codex session advertised sending as available but its Messenger send endpoint returned HTTP 502. A fresh Codex session replied successfully; the imported-session failure is tracked in the PH5.1 claim above.
- The earlier Memory-screen screenshot harness assumed the filename was automatically displayed in the note pane. The Memory screen lists notes first; opening `notes/morning-summary.md` exposed the saved body. This was a harness correction, not an application fix.

## Screenshots

Nine real-backend screenshots are in `evidence/ui/`:

- `final-01-build-context.png` — Build screen context in the assistant interaction.
- `final-02-codex-proposal.png`, `final-03-codex-refined.png`, `final-04-codex-accepted.png` — Codex proposal, one refinement, accepted graph and revealed nodes.
- `final-05-run-approval.png`, `final-06-memory-result.png` — approval gate and opened Memory result.
- `final-07-local-proposal.png` — Granite proposal.
- `final-08-messenger-claude.png` — opened Claude history thread with the read-only notice.
- `final-09-messenger-glacier.png` — Glacier thread's “garden confirmed” reply. The Codex fresh-thread reply is recorded above; its imported transcript is too verbose to make a useful screenshot.
