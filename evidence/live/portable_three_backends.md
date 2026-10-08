# Portable worker backend live bench

Run date: 2026-10-08

Drift check: PH2 exit M-PORTABLE; serves P-PORTABLE. PH1 is not at exit yet, so this evidence does not mark PH2 done. Existing two-harness ACP proof did not provide a repeatable three-backend swap. Acceptance: all three runs use the same goal, flow and independent check; only the worker backend field changes; every independent and Glacier check passes.

The runner first tried the coding goal. If any backend failed, it ran a smaller function-plus-test goal through all configured backends. Workspaces and Glacier data were temporary. No credentials or tokens are recorded.

## Coding

| Backend | Glacier | Independent | Seconds | Route |
|---|---:|---:|---:|---|
| Codex CLI | done / True | True | 13.31 | codex/chatgpt-plan |
| OpenCode ACP (Ollama qwen2.5-coder:7b) | failed / False | False | 9.28 | acp/opencode |
| OpenCode ACP (Ollama granite3.3:2b) | failed / False | False | 11.3 | acp/opencode |

Normalized flow diff (backend selector/config and temporary workspace path normalized): identical; backend field only

### Codex CLI

- Worker step type: `codex`
- Independent check output: `..                                                                       [100%]
2 passed in 0.00s`
- Worker output: `codex exit 0
Added `add(a, b)` in [math_ops.py](/tmp/glacier-portable-y0f86taj/workspace-coding-codex-cli/math_ops.py) and pytest coverage for positive values and zero in [test_math_ops.py](/tmp/glacier-portable-y0f86taj/workspace-coding-codex-cli/test_math_ops.py).

`pytest -q` passed: **2 tests**.`

### OpenCode ACP (Ollama qwen2.5-coder:7b)

- Worker step type: `acp_agent`
- Independent check output: `no tests ran in 0.00s`
- Worker output: `{
  "name": "todowrite",
  "arguments": {
    "todos": [
      {
        "content": "Create a function `add(a, b)` in `math_ops.py` that returns the sum",
        "priority": "high",
        "status": "pending"
      },
      {
        "content": "Create pytest tests in `test_math_ops.py` covering positive values and zero",
        "priority": "high",
        "status": "pending"
      },
      {
        "content": "Run the tests",
        "priority": "high",
        "status": "pending"
      }
    ]
  }
}`

### OpenCode ACP (Ollama granite3.3:2b)

- Worker step type: `acp_agent`
- Independent check output: `no tests ran in 0.00s`
- Worker output: ````json
{
  "command": "todowrite",
  "description": "Create and maintain a structured task list for the current coding session.",
  "prompt": "Add a function 'add(a, b)' in math_ops.py that returns the sum, and add pytest tests in test_math_ops.py covering positive values and zero. Run the tests using relative paths in this project; do not modify test files after adding them.",
  "subagent_type": "general",
  "task_id": "none"
}
````

## Simple Fallback

| Backend | Glacier | Independent | Seconds | Route |
|---|---:|---:|---:|---|
| Codex CLI | done / True | True | 7.74 | codex/chatgpt-plan |
| OpenCode ACP (Ollama qwen2.5-coder:7b) | failed / False | False | 20.4 | acp/opencode |
| OpenCode ACP (Ollama granite3.3:2b) | failed / False | False | 11.29 | acp/opencode |

Normalized flow diff (backend selector/config and temporary workspace path normalized): identical; backend field only

### Codex CLI

- Worker step type: `codex`
- Independent check output: `.                                                                        [100%]
1 passed in 0.00s`
- Worker output: `codex exit 0
Created [math_ops.py](/tmp/glacier-portable-y0f86taj/workspace-simple-codex-cli/math_ops.py) and [test_math_ops.py](/tmp/glacier-portable-y0f86taj/workspace-simple-codex-cli/test_math_ops.py). `pytest` passed: 1 test.`

### OpenCode ACP (Ollama qwen2.5-coder:7b)

- Worker step type: `acp_agent`
- Independent check output: `no tests ran in 0.00s`
- Worker output: `{"name": "write", "arguments": {"content": "def add(a, b):\n    return a + b", "filePath": "./math_ops.py"}}
{"name": "write", "arguments": {"content": "import pytest\nfrom math_ops import add\n\ndef test_add():\n    assert add(2, 3) == 5", "filePath": "./test_math_ops.py"}}
{"name": "command", "arguments": {"command": "pytest .", "workingDirectory": "."}}`

### OpenCode ACP (Ollama granite3.3:2b)

- Worker step type: `acp_agent`
- Independent check output: `no tests ran in 0.00s`
- Worker output: ````json
{
  "todos": [
    {
      "content": "Create ./math_ops.py with a function add(a, b) that returns a + b.",
      "priority": "medium",
      "status": "completed",
      "filePath": "./math_ops.py"
    },
    {
      "content": "Create ./test_math_ops.py with one pytest test that imports add from math_ops and asserts add(2, 3) == 5.",
      "priority": "medium",
      "status": "completed",
      "filePath": "./test_math_ops.py"
    },
    {
      "command": "pytest",
      "description": "Run pytest.",
      "params": {
        "filePath": ".\\test_math_ops.py"
      }
    }
  ]
}
````

## Result: FAIL

Coding goal across three backends: FAIL.
Coding goal flow diff: backend field only.
Three-backend portability rate for accepted goal: 1/3.
