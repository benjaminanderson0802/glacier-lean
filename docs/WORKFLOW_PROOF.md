# Workflow proof

Run on 2026-10-09 in the card/gf-A5 worktree. These checks start the actual FastAPI/Uvicorn backend in isolated temporary data folders; they do not use the web mock.

## Acceptance

From glacier/backend:

    /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_flows_real_runtime.py

Result: **22 passed**. The test module checked:

- A real cron tick ran a command, checked its output marker, wrote a versioned note, appeared in run history, and returned a plain-language run explanation. It also edited and undid the note through the memory API.
- A manual run sent input through Ollama granite3.3:2b, waited durably for approval across a forced backend restart, then ran the next command only after approval.
- A local HTTP server returned JSON; the HTTP request step passed the response to a local-model decision with two branches, and only the selected note branch ran.
- A two-iteration loop stopped at its configured limit, then called a child Environment. Both runs appeared in history.
- The DBOS-backed run survived a forced backend kill and restart. The finished first and last commands each ran once. The interrupted shell command is allowed to complete after the backend is killed and can be retried on recovery.
- The official Codex subscription CLI created hello.txt in a disposable folder; a separate command step verified the exact file content.
- Each of the 16 reviewed, installable entries in templates/manifest/MANIFEST.json was copied through the Environment save API and run against the real backend. Runtime-only folders and a local HTTP fixture kept these checks away from the user's data and the public network. The test-and-fix template used a small passing pytest project in its temporary workspace.

The installed Ollama model and signed-in Codex CLI were available for this run, so no optional engine cases were skipped. If either is absent in another environment, the associated tests skip with the required install/sign-in instruction.

Regression and screen checks also passed:

    flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests'
    # 742 passed, 1 skipped
    cd glacier/web && npx tsc -b
    cd glacier/web && node e2e/theme_lint.mjs
    # theme lint ok (45 files)
    cd glacier/web && node scripts/check-i18n.mjs --fail
    # 2 dictionaries, 766 keys; parity and placeholders match

## Template results

All passed: tpl-backup-check, tpl-daily-report, tpl-document-note, tpl-downloads-tidy, tpl-explain-error, tpl-folder-backup, tpl-folder-cleanup, tpl-inbox-triage, tpl-meeting-tasks, tpl-morning-brief, tpl-nightly-job, tpl-sub-flow-example, tpl-test-and-fix, tpl-web-change-watch, tpl-website-monitor, and tpl-weekly-research.

## Drift check

- Advances PH1.2/PH1.4 runtime integration proof, and verifies existing PH2 worker and PH5 explanation/template behavior. PH0 is at exit; PH1 is still in progress, so this work does not mark a roadmap checkpoint complete.
- Serves P-LOOPS, P-CONTROL, P-MEMORY, and P-PORTABLE; the relevant runtime measures are M-SURVIVE, M-AUDIT, and M-LOCAL.
- DBOS, MAF, Ollama, and the official Codex CLI already provide the engines. The added work is integration proof around those existing tools; no new engine or dependency was introduced.
- Acceptance is the real-backend test module above: exercise the requested workflow shapes, verify outcomes and side effects, cover recovery/approval/history/undo/explanation, and install/run every manifest-listed installable template.

## Anti-pattern review

The proofs run ordinary workflows through the backend and verify their effects; they are not mock-only tests or reports presented as working software. No engine defect requiring a runtime source change was reproduced. One restart-test assertion was corrected to account for an interrupted detached command completing after backend termination; it still proves that completed steps are not repeated.
