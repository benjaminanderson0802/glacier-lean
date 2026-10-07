# Verification benchmark cases

This benchmark checks whether a worker's result really meets a task's request.
It includes 10 ordinary tasks with known-good answers and 20 traps for common
false-success patterns, such as incomplete work, a changed local test, or a
correct answer saved under the wrong name. Each acceptance check runs separately
from the worker's success message and checks the actual files or behavior.

The cases provide repeatable inputs for measuring false-done and verified
completion rates. A run against a worker should count a task as done only when
its acceptance check passes. The validator here checks that each case is
well-formed and that its known-good and trap examples have the intended result;
it does not run an AI worker or calculate benchmark rates.

## Case format

Each `.yaml` file is a JSON-compatible YAML mapping, so it can be read with
Python's standard library and also by ordinary YAML readers. It contains:

- `id`, `title`, `goal`: the case identity and plain-language worker task.
- `setup_files`: small path-to-text fixtures created before the check.
- `acceptance_check`: a POSIX shell command using `python3 -c`; exit code 0
  means the task is done. Checks use only Python's standard library.
- `expected`: `pass` for a correct ordinary task, or `fail` for a trap.
- `trap`: `none` for ordinary tasks, or one of the supported trap types.
- `notes`: a short explanation of what the case catches.
- `good_solution_files`: files that must pass the independent check.
- `bad_solution_files`: present for trap cases; files that must fail it.

The check runs in a fresh temporary folder containing `setup_files` plus the
selected solution files. Trap checks run once with the good files and once with
the bad files, so a trap is valid only when good work passes and careless work
fails.

## Run it

From the repository root:

```sh
python3 bench/verification/validate.py
python3 -m pytest -q bench/verification/test_validate.py
```

The validator reports an error and exits non-zero if the schema, case count, or
any expected check result is wrong.
