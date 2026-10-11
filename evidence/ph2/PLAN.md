# E-PH2 verification plan (2026-10-10)

Owner authorization: Benjamin Anderson, E-PH2, maximize progress; commit only.

Drift check before implementation:

1. PH2.1–PH2.5: worker routing, Granite, subscription adapters, failure handling.
2. PH1 checkpoints are marked done; phase remains in_progress and its M-AUDIT
   exit is not re-established here. Assigned card permits work; no phase closure.
3. P-PORTABLE, P-VERIFY; M-PORTABLE, M-LOCAL, M-COST, M-FALSE-DONE.
4. Reuse installed Ollama, official subscription CLIs and existing Glacier
   adapters. Only adapter glue changes; no dependencies or paid services added.
5. Existing acceptance: test_gateway.py, test_gateway_preferred.py,
   test_local_ai.py, test_local_ai_answers.py, test_acp*.py, test_core.py,
   test_ask_context_pack.py, test_flows_real_runtime.py, bench/portable.
   These checks remain untouched. New ordinary parsing unit regressions precede
   implementation; baseline: 16 failed, 1 passed (unit-before.log).

Reproductions and assumptions: unconfigured gateway selects qwen3:0.6b contrary
to the approved Granite default; `choices: []` escapes fallback with IndexError;
an empty Ollama JSON object returns done with empty output. Treat malformed or
empty model answers as failures before recording success/usage, allowing gateway
fallback. A response with malformed usage is not a complete worker result.

Scope: gateway.py, nodes/local_ai.py, new ordinary unit tests, PH2 evidence and
claims, required amendment note. No existing checks, screen contract, mock, phase
criteria, settings, or owner-only hardware steps change.

Board constraint discovered before execution: setup/run_core_tests.sh installs
into the shared dependency directories and deletes fixed /tmp/e2edata, potentially
owned by another worker. setup/live_codex_check.sh hardcodes port 8000 and omits
the required install token. Run the existing board components and authenticated
real-backend tests in isolated homes instead; do not rewrite these judging checks.
