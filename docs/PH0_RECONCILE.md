# PH0 exit reconciliation

## Drift check and acceptance

- **Checkpoint:** PH0.1 core tools proof and PH0.4 prior systems disabled evidence.
- **Dependencies:** this assigned evidence follow-up may start while other phases are in progress; NORTHSTAR lists PH0 as done.
- **Property and metric:** P-PORTABLE / M-PORTABLE and I-01/I-09: the composed stack must use pinned open tools and prove the actual integrations.
- **Existing tooling:** the PH0 runner already checks pins, imports, licences, package installs, legacy paths, and repo setup. This change makes it read missing licence records, verifies documented replacements with existing tests, and inspects current launch/config files.
- **Acceptance test (written first):** `.venv/bin/python bench/ph0/run_ph0.py` reports all 12 PH0 claims PASS; replacement rows run their existing backend tests and the plain-text editor screen check; React Flow and xterm are found at their pinned versions after `npm ci`; the prior-systems row performs a current repo/setup inspection. If the screen test exits nonzero, the runner gives it one fresh-process retry and passes only if a complete run succeeds. No existing test or check is edited.

## Results before this card

Baseline command: `.venv/bin/python bench/ph0/run_ph0.py`.

| Result | Claim | Finding |
|---|---|---|
| FAIL | MAF workflows | `agent-framework-core==1.19.0` was installed and pinned; Python package metadata omitted its licence, and current production code did not import it. |
| PASS | DBOS | Pinned and importable; MIT metadata recorded. |
| FAIL | ACP | `agent-client-protocol==0.12.1` was installed and pinned; Python package metadata omitted its licence. |
| FAIL | Bifrost | Not installed as Python `bifrost`; later implemented as optional external gateway, while the default gateway is Glacier's built-in implementation. |
| PASS | vault + git + search | GitPython pinned/importable; BSD-3-Clause metadata recorded. |
| FAIL | AG-UI | `@ag-ui/client` was pinned but `node_modules` was absent; code inspection showed Glacier implements the protocol in its own API client. |
| FAIL | React Flow | Pinned package, but `node_modules` was absent. |
| FAIL | xterm | Pinned package, but `node_modules` was absent. |
| FAIL | Monaco | Pinned package, but `node_modules` was absent; code inspection showed the plain text note editor superseded it (PR #54). |
| PASS | sandbox/repo setup | Required repo and sandbox files present. |
| PASS | legacy paths mapped or removed | All 51 listed module paths reconciled. |
| FAIL | prior systems disabled | Existing evidence cited only a historical session log. |

This is 4 PASS / 8 FAIL. React Flow and xterm were installed from their existing pins. AG-UI
protocol handling and plain text editing were already implemented, so their package absences
were not treated as proof that those capabilities were missing.

## Results after this card

Final command: `.venv/bin/python bench/ph0/run_ph0.py`.

| Result | Claim | Finding |
|---|---|---|
| PASS | DBOS | `dbos==3.2.0`; pinned/importable; MIT package metadata. |
| PASS | ACP | `agent-client-protocol==0.12.1`; pinned/importable; Apache-2.0 from `setup/licenses.json`. |
| PASS | vault + git + search | GitPython pinned/importable; BSD-3-Clause package metadata. |
| PASS | MAF workflows | Replaced by DBOS workflows + local model/ACP adapters (PRs #6, #10); 53 replacement tests passed. |
| PASS | Bifrost | Replaced for the default route by Glacier's built-in gateway (PR #19); 6 gateway tests passed; Bifrost remains optional. |
| PASS | AG-UI | Replaced by Glacier's native event client (PRs #28, #52); 18 backend stream tests passed. |
| PASS | Monaco | Replaced by the plain text note editor (PR #54); `shell.spec.mjs` passed on its one allowed fresh-process retry. |
| PASS | React Flow | `@xyflow/react@12.12.0`; pinned, installed and MIT. |
| PASS | xterm | `@xterm/xterm@6.0.0`; pinned, installed and MIT. |
| PASS | sandbox/repo setup | Required repository and sandbox files present. |
| PASS | legacy paths mapped or removed | 51 mapped module paths checked; 3 keepers found. |
| PASS | prior systems disabled | 619 tracked paths and setup/deployment files inspected; no Forge task launch config or legacy container orchestration files found. |

Overall: **12/12 PASS**. The screen check passed on the runner's single fresh-process retry after
an initial splash-screen startup failure; the unchanged screen check also passed standalone.

## Findings and evidence

- **MAF:** it is pinned but unused in the production tree (`rg agent_framework glacier/backend` finds no production import). The later implementation uses DBOS for durable workflows and the native local model and ACP adapters. This is evidenced by the DBOS runner, PR #6 local-model worker, PR #10 ACP worker, and their existing backend tests. The runner reports MAF as replaced only when `tests/test_core.py`, `tests/test_local_ai.py`, and `tests/test_acp_agent.py` all pass. The pin remains in requirements until the integrator decides whether to remove the unused package in a separate scoped change.
- **ACP:** it is imported by `glacier/backend/nodes/acp_agent.py` and used by the harness worker. Upstream `agentclientprotocol/python-sdk` is Apache-2.0; `setup/licenses.json` records `Apache-2.0` for exact version 0.12.1.
- **Bifrost:** PR #19 added Glacier's built-in OpenAI-compatible gateway and its fallback tests. Bifrost remains an optional separate production service for centralized operational features (`setup/gateway/README.md`); the default model-gateway PH0 role is therefore reported as replaced only after the existing `tests/test_gateway.py` passes.
- **React Flow and xterm:** both are imported in the active screen and remain pinned; the runner reads their package metadata from `glacier/web/node_modules` after `npm ci`.
- **AG-UI:** `@ag-ui/client` is not imported. Glacier's API client parses the AG-UI event stream; the runner counts it only after the backend stream tests pass (PRs #28 and #52).
- **Monaco:** `@monaco-editor/react` is not imported. The plain text note editor landed in PR #54; the runner counts it only after the existing `shell.spec.mjs` check passes.
- **Prior systems:** the updated PH0.4 check inspects git-tracked paths and active setup/deployment config files for legacy Forge task launch references and old container orchestration files. It reports only the state inspectable in this checkout; it does not claim to inspect historical Windows machines.

## Proposed NORTHSTAR.yaml wording

The integrator should apply these exact text changes after review. No NORTHSTAR fields were edited in this card.

### PH0.1

Replace:

```yaml
{id: PH0.1, item: "Core tools proven in sandbox (MAF workflows, DBOS, ACP, Bifrost, vault+git+search, AG-UI, React Flow, xterm, Monaco)", status: done, evidence: "evidence/RESULTS.md; research doc 'Glacier Lean Stack'"}
```

With:

```yaml
{id: PH0.1, item: "Core tools proven in sandbox (DBOS workflows, local model and ACP adapters, Glacier built-in gateway; optional Bifrost; vault+git+search, AG-UI event protocol, React Flow, xterm, plain text note editor)", status: done, evidence: "bench/ph0/run_ph0.py; docs/STACK.md; setup/licenses.json; replacement tests tests/test_core.py, tests/test_local_ai.py, tests/test_acp_agent.py, tests/test_gateway.py, tests/test_assistant_chat.py, tests/test_ask_local_route.py, glacier/web/e2e/shell.spec.mjs"}
```

### PH2.2

Replace:

```yaml
{id: PH2.2, item: "Local-model worker (Ollama/llama.cpp) via MAF agent node", status: done, test: "local model completes a task offline; result verified", evidence: "PR #6 nodes/local_ai.py; backend tests with a fake Ollama server (offline); live model check on the owner's PC pending PC installs"}
```

With:

```yaml
{id: PH2.2, item: "Local-model worker (Ollama/llama.cpp) via Glacier's native model adapter", status: done, test: "local model completes a task offline; result verified", evidence: "PR #6 nodes/local_ai.py; backend tests with a fake Ollama server (offline); live model check on the owner's PC pending PC installs"}
```

### PH2.3

Replace:

```yaml
{id: PH2.3, item: "Model gateway (Bifrost) with per-node route, fallback chain and quota awareness", status: done, test: "primary unavailable → fallback used, logged, run still verified", evidence: "PR #19 gateway.py: fallback chain, daily caps, free-only (paid always refused, one policy claim per day); fake-server tests"}
```

With:

```yaml
{id: PH2.3, item: "Glacier built-in model gateway with per-node route, fallback chain and quota awareness (Bifrost optional)", status: done, test: "primary unavailable → fallback used, logged, run still verified", evidence: "PR #19 gateway.py: fallback chain, daily caps, free-only (paid always refused, one policy claim per day); fake-server tests"}
```

The PH0.4 item and status need no wording change: the runner now supplies a current inspectable
check instead of relying on the 2026-10-06 session log alone.
