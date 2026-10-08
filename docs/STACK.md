# Current Glacier stack

This records the tools the checkout actually installs and uses. Versions below match the
repository pins. SPDX identifiers are used for licence records.

| Tool or capability | Current implementation | Version | Licence | Evidence |
|---|---|---:|---|---|
| Durable workflows | DBOS Transact | 3.2.0 | MIT | `setup/requirements.txt`; `glacier/backend/runner.py` |
| Local model steps | Glacier's native Ollama adapter | repository code | Apache-2.0 repository | PR #6; `glacier/backend/nodes/local_ai.py` |
| Coding-agent protocol | ACP Python SDK | 0.12.1 | Apache-2.0 | `setup/requirements.txt`; `glacier/backend/nodes/acp_agent.py` |
| Default model routing | Glacier's built-in OpenAI-compatible gateway | repository code | Apache-2.0 repository | PR #19; `glacier/backend/gateway.py` |
| Separate production gateway | Bifrost remains optional | 1.6.3 when installed | Apache-2.0 | `setup/gateway/README.md`; it is not required for the default route |
| Canvas | `@xyflow/react` | 12.12.0 | MIT | `glacier/web/package.json`; `glacier/web/src/screens/Build.tsx` |
| Terminal | `@xterm/xterm` | 6.0.0 | MIT | `glacier/web/package.json`; `glacier/web/src/screens/TerminalPanel.tsx` |
| Code editor | `@monaco-editor/react` | 4.7.0 | MIT | `glacier/web/package.json` |
| AG-UI stream protocol | Glacier's event parser and API client | repository code | Apache-2.0 repository | PRs #28 and #52; `glacier/backend/routes/assistant_chat.py`, `glacier/web/src/api.ts` |
| Note editing | Glacier's plain text `NoteEditor` | repository code | Apache-2.0 repository | PR #54; `glacier/web/src/screens/NoteEditor.tsx` |

`agent-framework-core==1.19.0` remains pinned in the install requirements, but the current
production tree has no `agent_framework` import. The actual workflow and worker paths are
DBOS, Glacier's local model adapter, and ACP. Their behavior is checked by the existing core,
local-model, and ACP tests; the PH0 runner executes those checks before marking MAF replaced.
The machine-readable upstream licence record is in `setup/licenses.json` for environments
where Python package metadata omits the licence field.

`@ag-ui/client` and `@monaco-editor/react` remain in the npm manifest but are not imported by
the current screen: Glacier handles AG-UI events in its own API client, and the note editor is
plain text. The proof runner checks those replacements instead of treating an installed,
unused package as evidence. React Flow and xterm are imported directly; a fresh checkout must
install their pinned packages with `cd glacier/web && npm ci` before running the PH0 proof runner.
