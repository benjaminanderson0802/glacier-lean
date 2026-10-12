# C-ROOM-VISUAL-TESTER — Independently check the painted room and frosted-panel layout

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `room-visual-evaluator`. Allowed edits: new `glacier/web/e2e/room_visual_acceptance.spec.mjs` and `docs/ui/evidence/C-ROOM-VISUAL-TESTER/`. No screen, CSS, mock-server, translation or existing e2e edits. Run after M-FIX1 integrates so its screen files have one writer.

## Goal

Evaluate first-run/home, automations and ventures at 1280×800 and 1440×900 against `glacier/web/src/theme/limbo/room.webp`: painted-room composition, three frosted panels, Nunito, token-only colors and lowercase chrome. Report clipped content and hit-target failures with screenshots; do not tune the screenshot to the current code.

Read first: `docs/UI_HANDOFF.md`, `docs/ui/evidence/U-ROOM/PLAN.md`, `glacier/web/src/theme/ui.css`, `tokens.css`, and the M-FIX1 evidence when integrated.

## Drift check

- Checkpoint: PH5.4 and PH12.1 UI verification. PH5/PH9 remain in progress; the room evaluator is independent of M-FIX1 implementation.
- Properties/metrics: P-USABLE; M-INTERVENE (qualitative screen friction only; no user-study metric claim).
- Existing tools: current Playwright setup, theme lint and exact room.webp asset; no new visual framework.
- Acceptance first: screenshots at both viewports plus DOM assertions for lowercase room chrome and all three panels; manual comparison names the exact reference asset and records every mismatch.

## Verification

From `glacier/web`, run `npm run build`, `node e2e/theme_lint.mjs`, `node scripts/check-i18n.mjs --fail`, and the new spec. Keep all existing test IDs and behavior. Record any missing pinned dependency as an environment claim; do not change the lockfile.
