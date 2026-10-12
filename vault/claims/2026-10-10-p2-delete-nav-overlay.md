---
id: CLM-2026-10-10-P2-DELETE-NAV-OVERLAY
filed_by: Codex-P2
run_id: null
node_id: null
checkpoint: PH12.2
kind: bug
summary: Delete screen test cannot click memory navigation after builder flow deletion
evidence: ""
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

## Problem
The existing delete-screen e2e cannot click the `nav-memory` tab after deleting and undoing a flow in the builder.

## Evidence
Two fresh runs failed at `glacier/web/e2e/delete.spec.mjs:64`: the locator was visible, but the `.left.flows-open` aside intercepted pointer events. First: `flock /tmp/glacier-heavy.lock npm run check:ui`, where `business_nodes.spec.mjs` passed before `delete.spec.mjs` failed. Second: `flock /tmp/glacier-heavy.lock node e2e/delete.spec.mjs`, with the same interception. The existing test was left unchanged.

## Research

## Resolution
