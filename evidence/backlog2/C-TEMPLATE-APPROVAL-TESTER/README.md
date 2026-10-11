# C-TEMPLATE-APPROVAL-TESTER evidence

## Drift check

- Checkpoint: PH10.4, independent approval-snapshot evidence. PH8 and PH9 remain in progress; this card adds independent evidence and does not change checkpoint status.
- Depends on: PH10.4 is explicitly parallel-safe for this assigned evidence card; PH8/PH9 have not reached their exits.
- Properties and metrics: P-VERIFY, P-CONTROL, P-SECURE; M-VERIFIED, M-AUDIT, M-SECURITY.
- Existing tools: the public template import API, immutable reviewed snapshot, and pytest are sufficient. The test adds no review layer.
- Acceptance first: approval succeeds only for byte-equivalent reviewed command/capability content; changed proposals stay pending and non-installable. Unchanged content can be approved; encoded traversal and unknown step types are rejected; side-effect imports stay pending and absent from the gallery until approval.

## Verification

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/backlog/test_C_template_approval_snapshot.py
```

Result after installing the mock's pinned dependency: **1 failed, 1 passed**. The disposable real backend correctly exposed the current defect: changed command and added capability each approved, became installable, and left the pending store. Unchanged approval, encoded traversal, unknown step, and side-effect checks passed. The mock probe initially skipped because this worktree did not have `ws`; after installing pinned `ws@8.18.3` under `/tmp/c-template-approval-mock` and linking it into the existing untracked `node_modules`, the mock probe passed:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/backlog/test_C_template_approval_snapshot.py::test_current_screen_mock_exposes_template_gallery_but_not_import_api
```

Result: **1 passed**. `glacier/web/mock/mock_server.mjs` was not changed. The API and mock response captures are in `template-approval-snapshot-api.json` and `template-approval-snapshot-mock.json`.

The failing core check is intentional evidence of the unresolved claim, not a green acceptance result. Rerun this frozen test against the builder's candidate before relying on PH10.4 approval safety.
