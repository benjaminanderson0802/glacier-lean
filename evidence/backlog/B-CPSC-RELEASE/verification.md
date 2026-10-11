# B-CPSC-RELEASE verification

## Drift check

- Checkpoint: PH12.9, scoped reliability work only; no checkpoint status claim.
- Dependencies: PH12 depends on PH5 and PH9, still recorded in progress. The launch contract authorizes assigned PH12 work in parallel; this does not establish a phase exit.
- Properties and metrics: P-VERIFY and P-CONTROL; M-FALSE-DONE and M-VERIFIED.
- Existing-tool choice: the feed adapter already reports changes and the batch already parses the template. Small consumer glue now retains sync state, validates required mappings, and fingerprints the local feed records.
- Acceptance written before implementation: independent old/new template fixtures check exact column order, changed-template blocking, removed/added required-column blocking, refresh revision reporting, and deterministic output for an unchanged validated revision.

## Reproduction and fixture checks

Before the fix, the new regression fixture showed a changed template (`sync.changed: true`) still yielded CSV output. The returned batch had no `template_revision`. A missing required template column also had no template-level review gap.

The final CPSC suite command was:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/cpsc-prep/tests
```

Result: **26 passed, 1 skipped**. The skip is the existing opt-in live source canary. The new card-specific tests use synthetic feed rows and certificate fields; they do not certify or submit anything.

`git diff --check` passed.

## Real backend check

A real FastAPI backend was started with the project venv on `127.0.0.1:18765` and a fresh disposable `GLACIER_HOME` under `/tmp`. `GET /api/health` returned `{"ok":true}`. The process was stopped by the launching command after the health response.

This is real-backend availability evidence. CPSC template-change behavior was verified with independent local fixtures; no live CPSC sync or customer batch was run for this card. No certification, filing, publication, account, contract, or payment action occurred.
