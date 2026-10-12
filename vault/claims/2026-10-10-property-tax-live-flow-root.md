---
id: CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT
filed_by: Codex
run_id: ""
node_id: prepare_packet
checkpoint: PH12.17
kind: bug
summary: Property-tax flow commands cannot locate the venture script from Glacier's isolated command workspace, so the real packet flow fails before preparation.
evidence: evidence/ventures/property-tax-live-glacier.json
attempts_made: 2
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

The flow runner executes commands in an isolated workspace that has no repository checkout or `.git` directory. A `cwd: "{repo}"` setting was used literally and failed. The first replacement using `git rev-parse --show-toplevel` failed because the workspace is not a git checkout. A fallback `find` command returned the script file itself, and two live runs failed with `cd: can't cd to .../property_tax.py`.

Exact failed runs: `229a5a729228`, `98e0ea2c5227`, and `a43f0883bc53` (see linked evidence). The code owner must make the repository root or venture scripts available to command nodes, or provide a supported runtime variable for the checked-out project root. This venture worker stopped after the second attempt at the same root-discovery fix per NORTHSTAR escalation.

Do not mark PH12.17 complete until a fresh real Glacier run reaches packet preparation and records the expected `uncertain — please check` result for the public-row smoke case.
