# E-PH4 memory engine/API handoff

## Changes

- `10c3a64`: `vault.init` rebuilds disposable keyword/link rows from Markdown and JSON. A cloned vault is searchable without manual SQL; restarting reconciles offline edits/removals. The rebuild is transactional, preserves existing events, and writes no Git commit. Ordinary unit coverage checks clone recovery, repeat startup, external edits/removals, metadata exclusion and JSON search.
- `f825917`: `/api/memory/graph?limit=N` resolves the selected notes' links against all vault note paths. Older linked notes retain their resolved identities; their own outgoing links are not traversed. The response contract is unchanged, so no screen/mock change is needed.

## Verification

Commands run from `glacier/backend` with `~/w/glacier-lean/.venv/bin/python`:

| Command | Result | Evidence |
| --- | --- | --- |
| `-m pytest -q tests/test_vault_index_recovery_unit.py` before implementation | 3 failed, reproducing the missing/stale index | `index-recovery-before.log` |
| Same command after implementation | 3 passed | `index-recovery-after.log` |
| `-m pytest -q tests/test_memory_graph_limit_unit.py` before implementation | 2 failed, reproducing false missing links | `graph-limit-before.log` |
| Same command after implementation | 2 passed | `graph-limit-after.log` |

The broader unchanged memory tests were started before implementation; new backend subprocesses loaded the code present when they started. This run is diagnostic, not a clean final-code acceptance result. Its command was:

```
~/w/glacier-lean/.venv/bin/python -m pytest -q \
  tests/test_memory_reinstall_proof.py tests/test_memory_api.py \
  tests/test_memory_context.py tests/test_memory_links_exact.py \
  tests/test_memory_index.py tests/test_memory_hygiene.py \
  tests/test_memory_rename.py tests/test_memory_live.py
```

See `memory-baseline.log` for the complete output and final result.

From `glacier/web`:

- `npx tsc -b`: failed to locate the pinned TypeScript compiler (`typescript.log`).
- `node e2e/theme_lint.mjs`: passed, 52 files (`theme-lint.log`).
- `node scripts/check-i18n.mjs --fail`: failed, missing `typescript` in shared dependencies (`i18n.log`).

The missing dependency blocks build/browser checks. The full core board and live Codex check remain unverified; the legacy scripts have shared destructive paths/fixed ports and unauthenticated requests (see `PLAN.md`). No worker driver or UI file was changed.

## Live versus fixture evidence

The ordinary unit checks use real git/SQLite and temporary files, with direct API function calls for graph coverage. They do not prove live HTTP or a real model route. The unchanged memory suite uses real isolated backend processes and fixture worker/model engines; it never uses a real Codex/Ollama model.

A separate manual live attempt started the real backend with a disposable home, then the first note PUT exceeded its existing 30-second timeout. The intended clone/search/graph/undo sequence therefore did **not** complete (`live-recovery.log`). No live success is claimed for the new fixes.

## Final verification after the two fixes

The final PH4 backend acceptance batch was run against the committed code:

```
cd glacier/backend
~/w/glacier-lean/.venv/bin/python -m pytest -q \
  tests/test_memory_reinstall_proof.py tests/test_memory_api.py \
  tests/test_memory_context.py tests/test_memory_links_exact.py \
  tests/test_memory_index.py tests/test_memory_hygiene.py \
  tests/test_memory_rename.py tests/test_memory_live.py \
  tests/test_vault_index_recovery_unit.py tests/test_memory_graph_limit_unit.py
```

Result: **61 passed in 72.44 s**. This includes the unchanged
`test_memory_survives_full_reinstall_from_git` acceptance check. It starts real
isolated backend processes and verifies the HTTP, git clone/reinstall, keyword
search, graph, and undo paths using fixture data; it does not call a real model.
The new index-recovery and limited-graph tests are ordinary unit regressions,
not independent acceptance tests. A clean repeat passed **61 in 64.05 s**;
its captured output is in `memory-final.log`.

The full backend suite was also run under the shared lock. Its result is **829
passed, 1 skipped, 8 failed in 1424.95 s**; the complete output is in
`backend-full-final.log`. Failures were in assistant run-history behavior,
three server/template/model integration cases, and three Home counts/order
cases. None failed in the focused PH4 batch. They are outside this card's
memory-engine lane and remain unmodified.

The real backend + disposable vault HTTP attempt is still only a failed
diagnostic: its first note PUT timed out, so no manual live sequence is claimed.
The acceptance test above is real-backend/fixture verification, not a real
Codex/Ollama interoperability test. TypeScript and i18n checks remain blocked
by the absent shared `typescript` package; theme lint passed. No UI was changed,
so browser/UI acceptance was not part of this card.

## Remaining gate

All PH4 checkpoint rows were already marked done in NORTHSTAR. The memory
reinstall exit acceptance now passes, but PH4 depends on PH1, whose phase is
still marked `in_progress`; this card therefore does not mark the PH4 phase
complete. Real model interoperability and owner-only editor checks remain
separate, and no change was made to the owner-only PH4.10 check.

NORTHSTAR, existing tests, acceptance runners and ACCEPTANCE.md files are unchanged. PH4 is **not** newly marked complete. No dependencies were installed, no paid route was used, and no remote push was performed. The anti-pattern review found no need for an invariant amendment: preserve independent checks and avoid claiming completion from the builder's unit tests.

Changed production files: `glacier/backend/vault.py`, `glacier/backend/routes/memory.py`.
New ordinary unit tests: `glacier/backend/tests/test_vault_index_recovery_unit.py`, `glacier/backend/tests/test_memory_graph_limit_unit.py`.
Handoff artifacts: `evidence/E-PH4/*` and the environment claim in `vault/claims/`.
