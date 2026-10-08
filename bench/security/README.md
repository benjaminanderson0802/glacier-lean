# Security benchmark

This suite advances PH7.2 under P-SECURE and M-SECURITY. PH7 depends on PH3, which remains in progress; the assigned PH7.2 benchmark work is parallel-safe and does not change checkpoint status.

There is no existing security benchmark for prompt injection and API boundary attacks. `bench/verification` measures false completion and uses a separate case format, so this suite adds focused HTTP probes and run scenarios while reusing its local-backend pattern. It uses only the standard library and the repository's fake Codex executable.

Acceptance checks are `test_case_files_have_unique_ids_and_expected_outcomes` and the HTTP runner tests in `test_runner.py`. They validate 28 JSON cases, exercise blocked and unblocked probe outcomes against a fake API, and confirm the runner writes `Blocked: x/y` and exits nonzero when an attack succeeds.

Cases cover secret-bearing prompt injection framed as untrusted document, note, and tool output (fed through a command step to the fake Codex worker), secret placeholders in command-only execution and Codex refusal, I-04 protected acceptance checks, memory claim/path/author boundaries, paid gateway routes, restore/undo identifiers, and untrusted CORS origins. The injection scenarios scan run responses and persisted home files (including notes, claims, and alerts) for the in-memory keyring sentinel; the keyring test hook itself is excluded because it is harness setup, not a run output. Each secret-list case registers its own sentinel before reading the endpoint.

Probe scope notes:

- `flow-restore-ambiguous` currently checks the route's seven-character minimum commit-id rule. It does not establish that two valid-length commit ids collide.
- `environment-path-traversal` and `secret-name-traversal` currently check that encoded slash traversal is rejected by the API router with 404. They do not prove filesystem or keyring traversal defenses independently.
- `unknown-approval` checks that a nonexistent run cannot receive an approval. It does not test forged approval of a real waiting run.
- `memory-undo-ambiguous` generates a real ambiguous git prefix and keeps its result as a backend finding if undo accepts it.
- `run-undo-ambiguous` exercises exact run-id lookup: a real run id truncated to six characters must return 404, and an `abc` undo request must leave changes tagged for `abc123` untouched.

Run the suite with:

```sh
${GLACIER_PYTHON:-python} -m pytest -q bench/security
${GLACIER_PYTHON:-python} bench/security/run_glacier.py
```
