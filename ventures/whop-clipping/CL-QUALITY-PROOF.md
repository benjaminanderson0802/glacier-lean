# CL-QUALITY — implementation and validation

Owner: Benjamin. Card authorized 2026-10-11. Base: `fe1ccf208ee1720702f19b332944232d458fa1a3`, fetched from `origin/glacier-final` before editing. Commit only; no push, no live upload, and no changes to existing tests or `tests/acceptance`.

## Drift check and test-first plan

1. Advances the owner's CL-QUALITY final-adjustment card under PH12.22. The direct owner instruction raises the older OWNER-RULES six-post cap to eight per channel; no NORTHSTAR policy or phase status is changed.
2. PH12 depends on PH5 and PH9. Their top-level statuses remain in progress; this assigned card authorizes starting, not declaring a phase exit.
3. Serves P-VERIFY, P-LOOPS, P-CONTROL and M-VERIFIED, M-SURVIVE, M-AUDIT.
4. Reuses FFmpeg/libass, ffprobe, existing transcription and SQLite/event ledger. Custom code is campaign-specific glue and local review output; no paid service or new Python dependency. FFmpeg filter semantics: https://ffmpeg.org/ffmpeg-filters.html. Quota reference: https://developers.google.com/youtube/v3/determine_quota_cost.
5. Before implementing, added `tests/test_quality.py`; initial collection failed because `scripts.quality` did not exist. Generated testsrc2/sine fixtures exercise the actual media checks. Later regression cases exercise the same pipeline, capacity planning, 80-post schedule, review and quota boundaries. Existing judging checks remain unchanged.

## Delivered behavior

- Configurable 80 daily / eight per channel / 150-minute gap, default three-hour cadence. Legacy explicit configuration keys are honored until the private configuration is updated.
- Source moments are planned before rendering and weighted campaign shares are bounded by distinct candidate supply. Rendering and stocking remain incremental. Whop feedback reduces weights. No moments are duplicated to fill shortages.
- Captioned library previews and neutral bases; FFmpeg quality checks before stocking and after rendering the selected channel's variant. Dimensions, duration, black/freeze detection on base and variant, audio presence/loudness/true peaks/opening silence, early hook, timed captions and localized frame differences, brand spelling, tags, banned topics, all stocked/posted perceptual hashes and transcripts, and cross-channel time overlap are checked. Missing evidence fails closed.
- Transparent local 0–100 score with five components and default threshold 70. Highest scores receive slots first. Sentence punctuation is a completeness heuristic, not a semantic correctness guarantee.
- Pacific-date HTML review sheets rebuilt from events, escaped metadata and embedded thumbnail strips; explicit missing-thumbnail explanation for undecodable media. HOLD is checked before distribution and immediately before upload.
- Owner CSV results, last row per known clip, penalty `(accepted+1)/(accepted+rejected+1)`, reasons and quota allowance in status.
- Atomic project quota reservations include failed attempts and stop at 85 for the Pacific day. Quota stop preserves unused stock. All channels using this API project must share CLIP_HOME; unrelated external project use must be deducted via the configured cap.
- Separate crash-released Producer/Distributor locks prevent overlapping copies of each automation while allowing the Distributor to consume stock during production.

## Reproduce

Use the project's interpreter (`/home/glacier/w/glacier-lean/.venv/bin/python` in this sandbox). `/workspaces/glacier-lean/.venv/bin/python` is absent here.

FFmpeg is not on the default sandbox PATH. Validation used the real FFmpeg/ffprobe 7.0.2 static binaries extracted under `/tmp/cl-quality-tools/ffmpeg-7.0.2-amd64-static`, downloaded from `https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz`. No repository/runtime dependency was changed and no fake ffprobe was used.

```sh
export PATH=/tmp/cl-quality-tools/ffmpeg-7.0.2-amd64-static:$PATH
.venv/bin/python -m pytest -q ventures/whop-clipping/tests
.venv/bin/python -m pytest -q ventures/whop-clipping/tests/test_quality.py ventures/whop-clipping/tests/acceptance
.venv/bin/python ventures/whop-clipping/evidence/quality_live_smoke.py
cd glacier/web
npx tsc -b
node e2e/theme_lint.mjs
node scripts/check-i18n.mjs --fail
```

The backend smoke starts an isolated real uvicorn engine, saves/runs a command flow calling the actual Distributor entry point with HOLD, and checks `held: true`, `uploads: 0`, and a completed run. It stops only its own engine. Media integration tests additionally exercise real source-plan/render/stock and channel-render/recheck paths with local generated media and a recording uploader.

## Results and incomplete validation

See `evidence/quality-venture-tests.log`, `quality-targeted-tests.log`, `quality-live-backend.json`, `quality-theme.log`, `quality-tsc.log`, and `quality-i18n.log` for exact output. Final combined targeted run: **34 passed** (19 new regressions and all 15 unchanged independent acceptance cases). Full clipping suite: **120 passed, 1 skipped, 7 failed** in 56.61 seconds. Full venture suite is **not green**. Seven unchanged legacy tests expect non-media byte strings to pass QA (they stub the old dimensions/loudness-only probe); the spacing case also expects the old two-hour default. The new gate rejects those bytes. The source-error-reporting regression found during development was corrected. Tests were neither weakened nor edited to conceal the remaining failures.

TypeScript build and i18n check cannot run successfully: the worktree's pre-existing `glacier/web/node_modules` link lacks `typescript`. Theme lint passes (59 files). No Glacier UI files changed, so there are no affected screen e2e specs. No backend implementation/test files changed; the real-engine command-flow smoke supplies behavior proof.

`setup/run_core_tests.sh` was not run: it reinstalls the shared linked node_modules, deletes shared `/tmp/e2edata`, and starts a fixed-port server. This card does not change the platform or declare a phase checkpoint complete. Its required web commands were attempted individually and the backend smoke uses an isolated home/port. The worker-runtime `live_codex_check.sh` is not relevant to this venture-only change.

No production/private config or credentials were changed, and no real YouTube or Whop post was sent. No-edit clips without an independent base and timed-caption evidence remain rejected; this is an intentional fail-closed limit, not a verified no-edit caption capability. Output reaches 80 only when sufficient distinct clips pass all gates and channels are available.

The remaining test-fixture and environment work is recorded in `CL-QUALITY-FOLLOWUP.md`. No checkpoint is marked done. Anti-pattern review: no self-report is treated as passing evidence, no judging test is modified, and no unrelated platform/worker infrastructure is added. No NORTHSTAR amendment is proposed.

## File list

All changed files are inside `ventures/whop-clipping/`:

- `scripts/quality.py`, `scripts/policy.py` (new gate, review, feedback and defaults)
- `scripts/producer.py`, `scripts/distributor.py`, `scripts/campaigns.py`
- `scripts/ledger.py`, `scripts/interfaces.py`, `scripts/youtube_upload.py`
- `config.example.json`, `README.md`, `docs/YOUTUBE.md`
- `tests/test_quality.py` (new; existing tests unchanged)
- `CL-QUALITY-PROOF.md`, `CL-QUALITY-FOLLOWUP.md`
- `evidence/quality-venture-tests.log`, `quality-targeted-tests.log`, `quality-live-backend.json`, `quality_live_smoke.py`, `quality-theme.log`, `quality-tsc.log`, `quality-i18n.log`, `quality-sample-review.html`

The sample review contains generated test media, not real campaign content. The final targeted run follows the per-automation lock and already-stocked-clip guard refinements; the full-suite result immediately precedes those two refinements.
