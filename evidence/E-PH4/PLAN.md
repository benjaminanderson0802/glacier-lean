# E-PH4: memory engine recovery

Owner authorization: Benjamin Anderson, 2026-10-10, maximize progress on PH4 memory/API; commit only.

## Drift check, before implementation

1. PH4 exit (memory survives reinstall from git), PH4.1 keyword/link index recovery, and PH4.7 graph link resolution.
2. PH1 checkpoints PH1.1–PH1.7 are marked done; PH1's phase status remains in progress. The assigned card authorizes starting; phase completion is left to the integrator.
3. P-MEMORY and P-CONTROL; M-RECOVER (usable restored memory), M-AUDIT (preserve history and events).
4. Reuse the installed GitPython/git and SQLite FTS5 services. This is recovery glue for existing plain-file memory, not a new index engine. No new dependency or paid service.
5. Existing independent checks, unchanged: `tests/test_memory_reinstall_proof.py`, `test_memory_api.py`, `test_memory_links_exact.py`, `test_memory_live.py`, and the remaining memory/vault tests. New ordinary unit coverage is in `test_vault_index_recovery_unit.py`; it is not phase acceptance evidence by itself.

## Reproduced gap and assumptions

The existing reinstall acceptance runner manually rebuilds SQLite tables after cloning. Production `vault.init` creates empty tables but does not restore them from disk. A temporary local clone of a note containing `Lighthouse [[notes/research]]` produced:

```
Before clone: ['notes/decision.md']
After clone: []
Restored links: []
```

The fix will rebuild derived keyword/link rows from Markdown and JSON at startup, preserve the event table, and create no Git commit. An existing index must also reflect edits/removals made in an external editor while Glacier was stopped. Meaning search remains a separate optional local model index; the keyword fallback must work with no model.

## Verification constraints

`setup/run_core_tests.sh` uses shared `/tmp/e2edata`, port 8000, and `npm ci` against a node_modules symlink shared with other active workers. Run the same underlying checks with isolated homes/ports and the existing pinned environment instead of deleting shared data or replacing another worker's dependencies. Do not modify the setup scripts or acceptance checks. The legacy live Codex script also uses fixed port 8000 and unauthenticated requests; engine changes here do not change worker drivers.

Existing `.venv` and `glacier/web/node_modules` symlinks are environment setup, not card changes; exclude them from commits.
