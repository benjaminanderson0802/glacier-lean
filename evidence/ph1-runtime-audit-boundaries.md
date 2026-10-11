# PH1 runtime audit boundary evidence

Drift check: this advances PH1's exit criterion, serves P-CONTROL and M-AUDIT,
and closes the command side-effect gap that the existing audit trail did not
prove. The existing SQLite audit log is the appropriate open source facility;
these changes add runtime glue at command boundaries. Acceptance was written by
the independent tester in `glacier/backend/tests/test_C_runtime_audit_boundaries.py`.

## Runtime/audit acceptance

Command run from `glacier/backend`:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_C_runtime_audit_boundaries.py
```

Result: **5 passed**. This verifies durable start-before-effect ordering, known
done and failed outcomes correlated to the command attempt, one start/outcome
pair per retry attempt, explicit unknown outcome on interruption after an
effect, and an incomplete audit state when SQLite audit storage is unavailable.

Related backend tests:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests -k 'runner or audit or retry or durability'
```

Result: **58 passed, 1 skipped, 827 deselected**.

## Full backend board

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests
```

Result: **880 passed, 1 skipped, 5 failed**. The five failures were reproduced
with a targeted run (5 failed, 26 deselected) and are outside this card's
runtime/audit lane:

- `test_home_empty_state`, `test_home_collects_each_need_you_kind_and_counts_steps`,
  and `test_home_orders_and_caps_needs_and_notes` fail on `/api/home` need-you
  counts/row references.
- `tpl-email-inbox-note` fails because its email trigger reports
  `This step starts when a new email arrives`.
- `tpl-email-search-note` fails because `EMAIL_APP_PASSWORD` is unavailable.

The full board did not pass, so PH1 remains `in_progress`; the focused PH1 audit
acceptance and the related runtime/audit suites pass.
