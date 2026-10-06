# Glacier screen: handoff for a UI designer or design agent

You have full creative control over how Glacier looks and feels. This page lists the few fixed parts that make your screen plug into the working system with no rework. Your screen is accepted when `npm run check:ui` passes (see the end of this page).

## 1. What Glacier is (for design context)
Glacier lets anyone hand goals and recurring work to AI workers and ordinary automations, on their own computer, and accepts results only when an independent check proves them. Users draw **flows** made of **nodes** (steps) joined by **edges** (arrows), run them, watch each step live, approve risky steps, and browse what Glacier remembers.
Audience: **non-technical people first** (project rule). Plain words, no jargon, sensible defaults; technical detail available but never required.

## 2. Fixed parts (do not change)
1. **Data layer:** `glacier/web/src/api.ts` is the only code that talks to the backend. Use it as-is. You may add helpers on top of it, but no other `fetch` calls.
2. **Backend contract:** `docs/CONTRACT.md` (every request, response and live event). The screen holds no logic: it never decides whether a step passed, never writes files, never runs anything itself.
3. **Node types come from the backend:** `GET /api/node-types` (file `glacier/contract/node_types.json`). Build the palette, the settings form and the branch-label picker from it. Never hard-code a list of node types or their fields. Each field has `key, label, placeholder, default`, and optionally `optional`, `multiline`, `options` (a fixed choice list) or `picker: "environment"` (choose one of the saved flows).
4. **State vocabulary** (show these, style them however you like):
   - step states: `pending, running, done, failed, waiting, skipped`
   - run states: `running, waiting, done, failed, rejected`
   - branch labels: whatever the node type's `branches` says (today `yes/no` for check and approval, `again/done` for loop). A new edge from a branching node gets the first label, the second edge gets the other.
5. **Test labels:** keep a `data-testid` with the exact values below on the element that does that job. They are invisible to users.
6. **Technical limits:**
   - React + TypeScript + Vite, or anything else that builds to plain static files in `dist/`.
   - Works fully offline: no fonts, scripts or images loaded from the internet. Bundle everything; the screen ships inside a desktop app.
   - Only free, open-source libraries with permissive licenses (MIT, Apache-2.0, BSD, ISC). The project is Apache-2.0.
   - Must work in a window 1024 px wide and up.

## 3. Required features (what users must be able to do)
**Flows list:** see all flows; create a new one by name; switch between them (warn before discarding unsaved changes).
**Canvas (Build view):** add a node of any type from the palette; drag nodes; connect two nodes by dragging from one's output to another's input; select a node to edit its settings; select an edge to change its branch label; delete a node or edge; save (show that a save happened and its short commit id); run (saving first if needed). Arrows that close a loop must look different from ordinary arrows.
**Live run:** every node shows its live state while a run is going; the run's overall state is visible; selecting a node shows its output in a terminal-style panel; when a run waits for approval, show the question with Approve and Reject; selecting a sub-flow step offers "Open sub-flow run", which switches to that flow and shows its run.
**Run history:** list past runs of the current flow with state and time; selecting one shows its node states on the canvas; a way to go back to editing.
**Memory (today a simple list, a core feature soon):** list notes; open one to read it.
**Connection indicator:** show whether live updates are connected.

Coming soon. Leave room in the layout, no need to build yet:
- a chat panel with the assistant (plans a flow from plain language before running it);
- the simple **Run view**, next to the full **Build view**: finished automations, their status, and approvals only;
- the **Memory view**: a live graph of everything Glacier knows, focus mode with links in and out, a friendly editor, and who/when/which-run on every note;
- **Claims and proposals**: problems the AI could not solve, and paid-option proposals waiting for the owner;
- cost and model used per run.

## 4. Test labels (`data-testid`)
| Label | Element |
|---|---|
| `ws-status` (+ `data-connected="true|false"`) | live-connection indicator |
| `env-list`, `env-<flow id>` | flows list, one entry per flow |
| `new-env`, `new-env-name`, `new-env-create`, `new-env-cancel` | create-flow button, name input, confirm, cancel |
| `tab-canvas`, `tab-vault` | switch between canvas and memory |
| `palette`, `palette-<type>` | palette, one button per node type |
| `canvas` | the canvas area |
| `node-<node id>` (+ `data-state`, `data-type`) | each node; `data-state` is the live step state |
| `handle-in-<node id>`, `handle-out-<node id>` | each node's input and output connection points |
| `inspector`, `field-<field key>` | node settings panel, one input/select per field |
| `edge-inspector`, `edge-label` | edge panel, branch-label select |
| `delete-selected` | delete the selected node or edge |
| `env-name`, `env-id`, `dirty` | flow name input, flow id, unsaved marker |
| `save`, `run`, `last-commit`, `message` | save, run, last save's commit id, status message |
| `run-box`, `active-run-id`, `run-status`, `clear-run` | current run panel, its id, its state, back-to-editing |
| `run-list`, `runs-refresh`, `run-<run id>` (+ `data-status`) | run history, refresh, one entry per run |
| `approval-banner`, `approval-prompt`, `approve`, `reject` | approval request and its buttons |
| `terminal-panel`, `terminal-node`, `terminal-close` | output panel, which node it shows, close |
| `open-subrun` | open the sub-flow's run |
| `vault-refresh`, `vault-note-<path>`, `vault-note-body` | memory list refresh, one entry per note, open note text |

The canvas uses React Flow today (`.react-flow__edge`, `.react-flow__edge-text`, `.edge-loopback` classes are checked by the test). If you replace React Flow, keep those class names on edges, edge labels and loop-back edges, or update the test with the same checks.

## 5. How to work and how your screen is accepted
```
cd glacier/web
npm ci
npm run mock          # fake backend on :8787 with the same contract and node types (in-memory, nothing really runs)
npx vite --port 4173  # your screen, talking to the fake backend (set GLACIER_API=http://localhost:8787 if needed)
npm run check:ui      # type check + build + full browser test against the fake backend
```
Accepted when `npm run check:ui` prints `PASS` with no page errors. The project owner then runs the same test against the real backend.
Original Glacier visual reference, optional: `legacy-keep/` (retro design and assets).
