# C-ROOM-VISUAL-TESTER

## Drift check and acceptance (written before running the evaluator)

- **Checkpoint:** PH5.4 UI verification and PH12.1 UI verification. PH5 and PH9 remain in progress, so this evaluator supplies independent evidence only; it does not complete either checkpoint or the PH12 dependency gate.
- **Properties and metric:** P-USABLE and qualitative M-INTERVENE screen friction only. This is not a user-study or quantitative metric claim.
- **Existing tools:** reuse the installed Playwright setup, `theme_lint.mjs`, `check-i18n.mjs`, and the exact reference asset `glacier/web/src/theme/limbo/room.webp`. No new visual framework or dependency.
- **Acceptance test, before execution:** run `room_visual_acceptance.spec.mjs` at 1280×800 and 1440×900. Save first-run/home, automations, and ventures screenshots at both sizes. Assert lowercase room chrome, the three frosted panels, Nunito, exact room asset, and no horizontal page overflow. Record clipping and hit-target geometry with each screenshot. Manually compare every capture with the named asset and list each observed mismatch in `RESULTS.md`.

## Execution status

The evaluator was added, but execution is blocked by the empty `glacier/web/node_modules` tree: `npm run build` exits 127 with `tsc: not found`, and `npm ls typescript vite playwright --depth=0` reports no installed dependencies. The environment claim is [CLM-2026-10-11-C-ROOM-VISUAL-TESTER-PINNED-WEB-DEPENDENCIES-MISSING](../../../../vault/claims/2026-10-11-c-room-visual-tester-pinned-web-dependencies-missing.md). The lockfile was not changed. No independent screenshots, DOM results, or mismatch report are claimed yet.
