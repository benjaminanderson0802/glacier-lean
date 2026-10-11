---
id: CLM-2026-10-10-E-PH2-LIVE-GAPS
filed_by: E-PH2
run_id: null
node_id: null
checkpoint: PH2
kind: environment
summary: Claude live engine and shared legacy board require environment owner follow-up
evidence: evidence/ph2/PLAN.md
attempts_made: 0
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

`command -v codex claude ollama opencode` finds Codex, Ollama and OpenCode, but
no Claude CLI. Claude adapter checks can only use fixtures here. Installation
and subscription authentication remain an environment/owner step; no new service,
login reuse, paid route or dependency was adopted.

The legacy core script mutates shared .venv/node_modules and deletes a fixed
/tmp/e2edata. The live Codex script targets fixed port 8000 without authentication.
Neither is safe/reliable to run unchanged beside other workers. Prior claim
CLM-2026-10-10-A-APIFY3-SHARED-VALIDATION records the same core-board conflict.
Existing isolated backend tests and browser acceptance provide available proof;
the integrator owns modernizing the board scripts and independent verification.

PH2.6's real second-machine test stays an owner hardware step. No simulated
preferred-route test is presented as real laptop evidence.

Further observations during validation:

- `npx tsc -b` resolves an unrelated tsc package; the project TypeScript compiler
  is missing. `npm run build` fails with `tsc: not found`; i18n cannot import
  typescript and browser acceptance cannot import playwright. Theme lint passes.
  The pre-existing node_modules symlink targets the shared checkout; no shared
  dependency installation or test changes attempted.
- `test_local_ai_http_error_routes_check_no_with_model_hint` failed at backend
  startup (before invoking the node), with DBOS initialization exceeding the
  fixture's 60-second startup allowance. Reproduced in targeted and focused runs;
  no timeout changes or further isolated retry. See focused.log.
- Live engine tests skipped both Ollama cases because the availability probe
  failed, and Codex login status exceeded the existing 10-second timeout.
  Earlier command discovery found Granite installed and Codex signed in.
  Direct gateway calls also failed to reach the local model during this run.
  See live-engines.log and live-gateway.json. These are failed live attempts,
  not success evidence.
- Full backend invocation waited more than 11 minutes on the shared suite lock
  without starting pytest. Only this card's queued flock process was cancelled
  when parking the environment blocker; other workers and running suites were
  untouched. Full-board verification remains with the integrator.
