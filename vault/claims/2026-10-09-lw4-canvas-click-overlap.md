---
id: CLM-2026-10-09-LW4-CANVAS-CLICK-OVERLAP
filed_by: LW4-limbo-ui
run_id: null
node_id: null
checkpoint: PH5.4
kind: bug
summary: Flow editor side panel intercepts canvas node clicks after resizing to 1280x720
evidence: "From glacier/web, npx vite build && node e2e/core.spec.mjs: baseline reproduced section-head intercepting node-n1; after layout changes, repeated full runs still fail at e2e/core.spec.mjs:232 because active env-loop-flow button intercepts node-n1 after the test resizes from 1500x900 to 1280x720. A minimal fresh 1280x720 reproduction did not show the overlap. The test was not modified."
attempts_made: 4
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The issue appears only in the full test's accumulated-flow and viewport-resize sequence. The flow list row wins browser hit-testing at the node's click point even after constraining the left grid item, heading, and open-flow columns. Separate layer changes caused the canvas pane to intercept React Flow's Fit View button. I stopped further layout experiments under the NORTHSTAR self-fix limit. Reproduce with the original e2e at its viewport transition and inspect both the active row and node bounding boxes/hit targets before trying another layout change. The 1280x720 fresh-load case alone does not reproduce it.
