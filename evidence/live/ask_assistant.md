# Ask against the real assistant

Date: 2026-10-07. Five independent temporary backend homes; each home was removed after its run. The harness sent the same `POST /api/assistant/chat` body and consumed the same AG-UI event stream as `Ask.tsx`/`chat()`; approval and rejection used the screen’s proposal endpoint. `GLACIER_LOCAL_MODEL=granite3.3:2b` was set. However, the current chat route invokes Codex CLI for the answer and the planner defaults to Codex, so this is real backend + configured Codex assistant evidence, not an Ollama run.

## Results

| Prompt / action | Passes | Time to first text (s) | Total reply time (s) |
|---|---:|---:|---:|
| Plain question — `5/5` completed | 5/5 | 8.48, 5.44, 5.84, 5.78, 5.40 | 8.48, 5.44, 5.84, 5.78, 5.40 |
| Backup proposal — `5/5` completed | 5/5 | 15.47, 17.81, 15.53, 15.41, 15.36 | 15.47, 17.81, 15.53, 15.41, 15.36 |

Approval saved the flow and returned an undo ID in 5/5 runs. Rejection discarded the second proposal without creating a flow in 5/5 runs. Approved proposals necessarily passed the backend validation path in `apply_proposal`; each returned `saved: true`. All five generated plans included at least one acceptance check.

The second backup request in every run produced another valid proposal, so the benchmark did **not** observe a model-generated invalid plan. The no-network unit test feeds a `RUN_ERROR` event through the client parser and confirms it surfaces the plain message `The assistant could not answer. Please try again.` A model-generated invalid plan remains unobserved in live runs. The dry-run fakes the Ask HTTP transport; it cannot exercise a fake Ollama because this chat route invokes Codex CLI and the planner defaults to Codex. No backend code was changed.

## Raw proposals

Full raw HTTP proposal payloads are included below for direct review. Per-reply event timing and action results are summarized above.

### Run 1

```json
{
  "id": "9ff6efca-4930-4d0c-88e6-add7ea89e98d",
  "conversation_id": "089737df-fe4d-4a2d-8bda-14f4d89058db",
  "flow": {
    "id": "every-weekday-at-9-back-up-my-documents-",
    "name": "Weekday Documents backup",
    "goal": "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed",
    "nodes": [
      {
        "id": "schedule",
        "type": "schedule",
        "config": {
          "cron": "0 9 * * 1-5"
        },
        "position": {
          "x": 60,
          "y": 60
        }
      },
      {
        "id": "backup",
        "type": "command",
        "config": {
          "cmd": "zip -r \"$HOME/Documents-backup-$(date +%Y-%m-%d).zip\" \"$HOME/Documents\"",
          "cwd": "$HOME",
          "retries": "0",
          "timeout": "3600"
        },
        "position": {
          "x": 320,
          "y": 60
        }
      },
      {
        "id": "result",
        "type": "check",
        "config": {
          "expr": "exit_code == 0"
        },
        "position": {
          "x": 580,
          "y": 60
        }
      },
      {
        "id": "success_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup succeeded. Output: {{backup.output}}"
        },
        "position": {
          "x": 840,
          "y": 60
        }
      },
      {
        "id": "failure_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup FAILED (exit code {{backup.exit_code}}). Output: {{backup.output}}"
        },
        "position": {
          "x": 60,
          "y": 200
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "schedule",
        "target": "backup",
        "label": ""
      },
      {
        "id": "e2",
        "source": "backup",
        "target": "result",
        "label": ""
      },
      {
        "id": "e3",
        "source": "result",
        "target": "success_note",
        "label": "yes"
      },
      {
        "id": "e4",
        "source": "result",
        "target": "failure_note",
        "label": "no"
      }
    ],
    "acceptance": [
      {
        "kind": "command",
        "cmd": "test -d \"$HOME/Documents\" && command -v zip >/dev/null"
      }
    ],
    "created_by": "assistant"
  },
  "explanation": "This flow runs every weekday at 9:00 and creates a dated zip archive of your Documents folder. It checks the command result and records whether the backup succeeded or failed, including the command output and exit code.",
  "problems": []
}
```

### Run 2

```json
{
  "id": "8430f96e-6bc0-4be6-83d5-33bea09f2903",
  "conversation_id": "96ac8073-9e20-49bc-8e2d-3022d53b73c8",
  "flow": {
    "id": "every-weekday-at-9-back-up-my-documents-",
    "name": "Weekday Documents ZIP backup",
    "goal": "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed",
    "nodes": [
      {
        "id": "schedule",
        "type": "schedule",
        "config": {
          "cron": "0 9 * * 1-5"
        },
        "position": {
          "x": 60,
          "y": 60
        }
      },
      {
        "id": "backup",
        "type": "command",
        "config": {
          "cmd": "zip -r \"$HOME/Documents-backup-$(date +%F).zip\" \"$HOME/Documents\"",
          "cwd": "$HOME",
          "retries": "1",
          "timeout": "3600"
        },
        "position": {
          "x": 320,
          "y": 60
        }
      },
      {
        "id": "result_check",
        "type": "check",
        "config": {
          "expr": "exit_code == 0"
        },
        "position": {
          "x": 580,
          "y": 60
        }
      },
      {
        "id": "success_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup succeeded. Output: {{backup.output}}"
        },
        "position": {
          "x": 840,
          "y": 60
        }
      },
      {
        "id": "failure_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup FAILED (exit code {{backup.exit_code}}). Output: {{backup.output}}"
        },
        "position": {
          "x": 60,
          "y": 200
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "schedule",
        "target": "backup",
        "label": ""
      },
      {
        "id": "e2",
        "source": "backup",
        "target": "result_check",
        "label": ""
      },
      {
        "id": "e3",
        "source": "result_check",
        "target": "success_note",
        "label": "yes"
      },
      {
        "id": "e4",
        "source": "result_check",
        "target": "failure_note",
        "label": "no"
      }
    ],
    "acceptance": [
      {
        "kind": "rubric",
        "rubric": "A weekday 9:00 AM schedule triggers a ZIP backup of the Documents folder, branches based on the backup exit code, and records the result with failure details when unsuccessful."
      }
    ],
    "created_by": "assistant"
  },
  "explanation": "This flow runs every weekday at 9:00 AM and creates a ZIP archive of your Documents folder. It checks the command result and records whether the backup succeeded or failed, including any command output for troubleshooting.",
  "problems": []
}
```

### Run 3

```json
{
  "id": "cc0e3cc0-1771-4ee2-9f3b-edfdc3fa3705",
  "conversation_id": "c99d814e-348a-468e-b9f1-7dcc1239240f",
  "flow": {
    "id": "every-weekday-at-9-back-up-my-documents-",
    "name": "Weekday Documents backup",
    "goal": "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed",
    "nodes": [
      {
        "id": "schedule",
        "type": "schedule",
        "config": {
          "cron": "0 9 * * 1-5"
        },
        "position": {
          "x": 60,
          "y": 60
        }
      },
      {
        "id": "backup",
        "type": "command",
        "config": {
          "cmd": "zip -r \"$HOME/Documents-backup-$(date +%F).zip\" \"$HOME/Documents\"",
          "cwd": "$HOME",
          "retries": "0",
          "timeout": "3600"
        },
        "position": {
          "x": 320,
          "y": 60
        }
      },
      {
        "id": "result_check",
        "type": "check",
        "config": {
          "expr": "exit_code == 0"
        },
        "position": {
          "x": 580,
          "y": 60
        }
      },
      {
        "id": "success_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup succeeded at {{timestamp}}. Archive: $HOME/Documents-backup-$(date +%F).zip"
        },
        "position": {
          "x": 840,
          "y": 60
        }
      },
      {
        "id": "failure_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup FAILED at {{timestamp}}. Exit code: {{exit_code}}. Output: {{output}}"
        },
        "position": {
          "x": 60,
          "y": 200
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "schedule",
        "target": "backup",
        "label": ""
      },
      {
        "id": "e2",
        "source": "backup",
        "target": "result_check",
        "label": ""
      },
      {
        "id": "e3",
        "source": "result_check",
        "target": "success_note",
        "label": "yes"
      },
      {
        "id": "e4",
        "source": "result_check",
        "target": "failure_note",
        "label": "no"
      }
    ],
    "acceptance": [
      {
        "kind": "rubric",
        "rubric": "The flow runs at 9:00 on weekdays, creates a zip archive from Documents, checks the backup command's exit code, and records success or failure with details."
      }
    ],
    "created_by": "assistant"
  },
  "explanation": "This flow runs every weekday at 9:00 and creates a dated zip archive of your Documents folder. It checks the command result and records whether the backup succeeded or failed, including the error details when available.",
  "problems": []
}
```

### Run 4

```json
{
  "id": "c099732d-e0fc-48e9-b379-e7ef2b182d23",
  "conversation_id": "acf16ac5-67a9-4bf6-8f55-71ab52ee8ceb",
  "flow": {
    "id": "every-weekday-at-9-back-up-my-documents-",
    "name": "Weekday Documents Backup",
    "goal": "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed",
    "nodes": [
      {
        "id": "schedule",
        "type": "schedule",
        "config": {
          "cron": "0 9 * * 1-5"
        },
        "position": {
          "x": 60,
          "y": 60
        }
      },
      {
        "id": "backup",
        "type": "command",
        "config": {
          "cmd": "zip -r \"$HOME/Documents-backup-$(date +%Y-%m-%d).zip\" \"$HOME/Documents\"",
          "cwd": "$HOME",
          "retries": "0",
          "timeout": "3600"
        },
        "position": {
          "x": 320,
          "y": 60
        }
      },
      {
        "id": "result_check",
        "type": "check",
        "config": {
          "expr": "previous.exit_code == 0"
        },
        "position": {
          "x": 580,
          "y": 60
        }
      },
      {
        "id": "success_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup succeeded at {{timestamp}}. Archive: $HOME/Documents-backup-$(date +%Y-%m-%d).zip"
        },
        "position": {
          "x": 840,
          "y": 60
        }
      },
      {
        "id": "failure_note",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup FAILED at {{timestamp}}. Exit code: {{previous.exit_code}}. Output: {{previous.output}}"
        },
        "position": {
          "x": 60,
          "y": 200
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "schedule",
        "target": "backup",
        "label": ""
      },
      {
        "id": "e2",
        "source": "backup",
        "target": "result_check",
        "label": ""
      },
      {
        "id": "e3",
        "source": "result_check",
        "target": "success_note",
        "label": "yes"
      },
      {
        "id": "e4",
        "source": "result_check",
        "target": "failure_note",
        "label": "no"
      }
    ],
    "acceptance": [
      {
        "kind": "command",
        "cmd": "test -d \"$HOME/Documents\""
      },
      {
        "kind": "rubric",
        "rubric": "The flow runs at 9:00 AM Monday through Friday, creates a zip of Documents, branches on the command exit code, records the outcome, and makes failure details available."
      }
    ],
    "created_by": "assistant"
  },
  "explanation": "This flow runs every weekday at 9:00 AM and creates a dated zip archive of your Documents folder. It checks the command result and records whether the backup succeeded or failed, including the error output when available.",
  "problems": []
}
```

### Run 5

```json
{
  "id": "b49be124-e6a8-4518-9bd3-7539f808a340",
  "conversation_id": "c9cc2a09-4056-4262-85d2-7325e13a6c58",
  "flow": {
    "id": "every-weekday-at-9-back-up-my-documents-",
    "name": "Weekday Documents backup",
    "goal": "Every weekday at 9, back up my Documents folder to a zip and tell me if it failed",
    "nodes": [
      {
        "id": "schedule",
        "type": "schedule",
        "config": {
          "cron": "0 9 * * 1-5"
        },
        "position": {
          "x": 60,
          "y": 60
        }
      },
      {
        "id": "backup",
        "type": "command",
        "config": {
          "cmd": "zip -r \"$HOME/Documents-backup-$(date +%F).zip\" \"$HOME/Documents\"",
          "cwd": "$HOME",
          "retries": "0",
          "timeout": "3600"
        },
        "position": {
          "x": 320,
          "y": 60
        }
      },
      {
        "id": "result",
        "type": "check",
        "config": {
          "expr": "previous.exit_code == 0"
        },
        "position": {
          "x": 580,
          "y": 60
        }
      },
      {
        "id": "success",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup succeeded at {{timestamp}}. Archive: $HOME/Documents-backup-$(date +%F).zip"
        },
        "position": {
          "x": 840,
          "y": 60
        }
      },
      {
        "id": "failure",
        "type": "note",
        "config": {
          "path": "backups/documents/latest",
          "template": "Documents backup FAILED at {{timestamp}}. Exit code: {{previous.exit_code}}. Output: {{previous.output}}"
        },
        "position": {
          "x": 60,
          "y": 200
        }
      }
    ],
    "edges": [
      {
        "id": "e1",
        "source": "schedule",
        "target": "backup",
        "label": ""
      },
      {
        "id": "e2",
        "source": "backup",
        "target": "result",
        "label": ""
      },
      {
        "id": "e3",
        "source": "result",
        "target": "success",
        "label": "yes"
      },
      {
        "id": "e4",
        "source": "result",
        "target": "failure",
        "label": "no"
      }
    ],
    "acceptance": [
      {
        "kind": "rubric",
        "rubric": "The flow runs weekdays at 9:00 AM, creates a zip archive of Documents, checks the command exit code, and records success or failure details in a note."
      }
    ],
    "created_by": "assistant"
  },
  "explanation": "Runs every weekday at 9:00 AM and creates a dated zip archive of your Documents folder. It checks the backup command’s result and records whether it succeeded or failed. If the command fails, the recorded result will show the failure details.",
  "problems": []
}
```
