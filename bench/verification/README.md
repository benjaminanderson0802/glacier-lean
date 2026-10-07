# Verification benchmark cases

This benchmark measures whether a worker's result really meets a task's request.
It includes 10 ordinary tasks with known-good answers and 20 traps for false
success patterns, including incomplete work, changed local tests, hidden errors,
flaky behavior, and correct output saved under the wrong name. A task counts as
done only when its independent acceptance check passes.

## Case format

Each `.yaml` case file is JSON-formatted YAML. It can be loaded as JSON by
Python's standard library, with no extra package. Each case contains:

- `id`, `title`, `goal`: identity and plain-language task for the worker.
- `setup_files`: starter files, written before the worker's solution.
- `acceptance_check`: POSIX shell command using `python3 -c` and Python's
  standard library. Exit code 0 means the work is done.
- `expected`: `pass` for an ordinary case, or `fail` for a trap.
- `trap`: `none` or one of the supported false-success patterns.
- `notes`: what the case is designed to catch.
- `good_solution_files`: known-correct output, which must pass the check.
- `bad_solution_files`: careless or cheating output in trap cases, which must
  fail the same check.

The validator creates a temporary folder for each run. It writes the setup and
selected solution files, then runs the acceptance check. For traps, it verifies
both that the good output passes and the bad output fails. Test-edit traps hash
and run the original `test_task.py` as well as checking the result directly.
Flaky cases call the target repeatedly to expose inconsistent results.

## Run it

From the repository root:

```sh
python3 bench/verification/validate.py
python3 -m pytest -q bench/verification/test_validate.py
```

The validator reports an error and exits non-zero if a case is malformed or a
known good/bad example has the wrong result.
