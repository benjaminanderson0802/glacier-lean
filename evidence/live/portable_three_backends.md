# Portable worker backend live bench

Run date: 2026-10-08

Drift check: PH2 exit M-PORTABLE; serves P-PORTABLE. PH1 is not at exit yet, so this evidence does not mark PH2 done. Existing two-harness ACP proof did not provide a repeatable three-backend swap. Acceptance: all three runs use the same goal, flow and independent check; only the worker backend field changes; every independent and Glacier check passes.

The runner first tried the small coding goal. If any backend failed, it ran a simpler exact-file goal through all three. Workspaces and Glacier data were temporary. No credentials or tokens are recorded.

## Coding

| Backend | Glacier | Independent | Seconds | Route |
|---|---:|---:|---:|---|
| Codex CLI | done / True | True | 14.82 | codex/chatgpt-plan |
| OpenCode ACP | failed / False | False | 13.31 | acp/opencode |
| Ollama granite3.3:2b | failed / False | False | 6.26 | local/ollama |

Normalized flow diff (backend selector/config and temporary workspace path normalized): identical; backend field only

### Codex CLI

- Worker step type: `codex`
- Independent check output: `..                                                                       [100%]
2 passed in 0.00s`
- Worker output: `codex exit 0
Added `add(a, b)` in [math_ops.py](/tmp/glacier-portable-jv_u4exr/workspace-coding-codex-cli/math_ops.py) and tests for positive values and zero in [test_math_ops.py](/tmp/glacier-portable-jv_u4exr/workspace-coding-codex-cli/test_math_ops.py).

`python -m pytest` passed: 2 tests.`

### OpenCode ACP

- Worker step type: `acp_agent`
- Independent check output: `no tests ran in 0.00s`
- Worker output: ````
{
  "function": "todowrite",
  "parameters": {
    "todos": [
      {
        "content": "In math_ops.py, add a function `add(a, b)` that returns the sum.",
        "priority": "medium",
        "status": "pending"
      },
      {
        "content": "In test_math_ops.py, add pytest tests for `add(a, b)` covering positive values and zero.",
        "priority": "medium",
        "status": "pending"
      }
    ]
  }
}
```

To perform the tasks, the following steps will be taken:

1. In `math_ops.py`, add the function `add(a, b)` that returns the sum.

2. In `test_math_ops.py`, write pytest tests for `add(a, b)` covering positive values and zero.

After executing these steps, the tasks are marked as `in_progress`. Once completed, mark them as `completed`.

Please note that due to the limitations of this text-based interface, I cannot directly execute these tasks for you. You will have to create the files and write the code yourself or provide the content in the 'content' field of the "todos" array for the tool to perform these actions.`

### Ollama granite3.3:2b

- Worker step type: `local_ai`
- Independent check output: `no tests ran in 0.00s`
- Worker output: `/
│
├── math_ops.py
│
└── test_math_ops.py
```

2. Add the following code to `math_ops.py`:

```python
# math_ops.py

def add(a, b):
    """
    Adds two numbers and returns the sum.

    :param a: First number
    :param b: Second number
    :return: Sum of a and b
    """
    return a + b
```

3. Add the following code to `test_math_ops.py` using relative paths:

```python
# test_math_ops.py

import pytest
from math_ops import add

def test_add_positive_values():
    """
    Tests adding two positive numbers.
    """
    assert add(2, 3) == 5

def test_add_zero():
    """
    Tests adding a number and zero.
    """
    assert add(5, 0) == 5
```

4. To run the tests, open your terminal, navigate to the project root directory, and execute:

```bash
pytest
```

These tests will cover positive values and zero. The `pytest` command will automatically discover and run the test functions in `test_math_ops.py`.

Note: Make sure you have `pytest` installed in your Python environment. If not, you can install it using pip:

```bash
pip install pytest
```

This setup ensures that the test files remain independent and can be easily updated or extended without affecting the main project files.`

## Simple Fallback

| Backend | Glacier | Independent | Seconds | Route |
|---|---:|---:|---:|---|
| Codex CLI | done / True | True | 7.59 | codex/chatgpt-plan |
| OpenCode ACP | failed / False | False | 4.06 | acp/opencode |
| Ollama granite3.3:2b | failed / False | False | 3.06 | local/ollama |

Normalized flow diff (backend selector/config and temporary workspace path normalized): identical; backend field only

### Codex CLI

- Worker step type: `codex`
- Independent check output: `hello.txt exact content check`
- Worker output: `codex exit 0
Created `./hello.txt` with exactly this content:

```text
hello from glacier
````

### OpenCode ACP

- Worker step type: `acp_agent`
- Independent check output: `hello.txt exact content check`
- Worker output: `I've executed a new task. Here's the status:
- Todo List:
  - `in_progress`: Create './hello.txt' in the project folder with the exact content 'hello from glacier.'

Please confirm if you want to proceed with this task.`

### Ollama granite3.3:2b

- Worker step type: `local_ai`
- Independent check output: `hello.txt exact content check`
- Worker output: `To create a file named `hello.txt` in your project directory with the content "hello from glacier" using a relative path `./hello.txt`, you can use the following command in your terminal or command prompt:

```bash
touch ./hello.txt
```

After executing this command, a new empty file named `hello.txt` will be created in your project directory. To write the content "hello from glacier" into the file, you can use a text editor or redirect the output of the `echo` command:

For Unix-based systems (like Linux or macOS), you can use:
```bash
echo "hello from glacier" > ./hello.txt
```

For Windows Command Prompt, you can use:
```cmd
echo hello from glacier > ./hello.txt
```

These commands will create a file named `hello.txt` in your project directory with the desired content.`

## Result: FAIL

Coding goal across three backends: FAIL.
Coding goal flow diff: backend field only.
Three-backend portability rate for accepted goal: 1/3.
