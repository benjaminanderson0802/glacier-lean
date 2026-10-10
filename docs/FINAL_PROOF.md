# Final proof

## Card C3 — source-aware UI change proposals

Verified on 2026-10-09 against a real backend and Vite screen. From Ask on the Build screen, I asked Codex to make the
Home title say “welcome home.” The review-only card appeared in about 47 seconds. I approved it; the separate
`assistant/ui-change/ebe92759-adef-4791-b6bf-e1e5599663bd` branch was created at commit
`e4a2de15ae51aee5e8a81cec5f372707d7fb3749`. It changes `glacier/web/src/i18n/en.ts` (`home.title`) and the apply gate
reported TypeScript, theme lint, build, and `glacier/web/e2e/home_polish.spec.mjs` all passed. The main checkout stayed
unchanged. The retained live worktree is under `/tmp/glacier-c3-live-home/worktrees/ui-changes/` on the proof machine.

The masked screenshot `evidence/ui/c3-local-proposal.png` shows the live UI change card. The Codex proposal and approved
state were also captured during the live run, but those screenshots included unrelated Ask messenger thread titles, so
they were removed from this evidence set.

The local Ollama route (`granite3.3:2b`) returned a review card after the related-spec fallback was added. Its explanation
and proposed change did not address the requested Home title, so I discarded it without applying it. This proves that
the local route can return a card; it does not prove useful proposal quality for this request.

The local model route was exercised through the real browser and backend; it is not yet reliable enough to count as a
successful semantic change. OpenAI/Anthropic API, Claude CLI, Gemini CLI, and OpenCode were covered by the routing and
fake-engine paths only; they were not available or exercised against their real providers in this proof.

### Automated checks

- `cd glacier/backend && ../../.venv/bin/python -m pytest -q tests -n 4 -m "not serial"`: 768 passed, 1 skipped.
- `cd glacier/backend && ../../.venv/bin/python -m pytest -q tests -m serial`: 5 passed.
- From `glacier/web`: `npm run build`, `npx tsc -b`, `node e2e/theme_lint.mjs`,
  `node scripts/check-i18n.mjs --fail`, `node e2e/ui_change.spec.mjs`, `node e2e/ask_context.spec.mjs`, and
  `node e2e/messenger.spec.mjs`: all passed.
- The fake Codex worktree proposal, out-of-scope edit rejection, missing-source response, validated
  `glacier_source_dir` setting, model edit-block application, and one repair request passed in the focused backend tests.
