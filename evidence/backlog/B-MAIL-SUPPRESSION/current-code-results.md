# B-MAIL-SUPPRESSION independent acceptance baseline

Acceptance cases in `independent_acceptance.py` were derived from `ventures/SPEC.md`,
“Public-records mail engine”: suppression applies, a request added before a later
attempt is honored, and no suppressed postcard reaches the postal API.

Run on the current implementation (before the builder's changes):

```text
./.venv/bin/python -m pytest -q evidence/backlog/B-MAIL-SUPPRESSION/independent_acceptance.py
```

Result: **2 failed, 5 passed in 0.06s** (pytest process exit 1).

Failures:

- `whitespace-punctuation-and-field-aliases`: expected `fail` (suppressed), got `pass`.
- `test_zip_plus_four_and_five_digit_zip_represent_same_postal_address`: expected `fail` (suppressed), got `pass`.

Passing cases:

- case-insensitive spelling;
- same apartment is suppressed while a different apartment at the same building passes;
- UTF-8 plain-text list survives an engine module reload and remains readable;
- a request added after a first passing check blocks the subsequent attempt;
- suppressed postcard raises before the fake postal transport receives a request.

The shared interpreter path documented in the supplied `AGENTS.md`
(`/workspaces/glacier-lean/.venv/bin/python`) is absent in this checkout. The
workspace `.venv` symlink resolves to `/home/glacier/w/glacier-lean/.venv`; the
run above used the local `.venv` path.
