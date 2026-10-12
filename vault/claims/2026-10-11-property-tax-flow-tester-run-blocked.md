---
id: CLM-2026-10-11-PROPERTY-TAX-FLOW-TESTER-RUN-BLOCKED
filed_by: Codex
run_id: "852c69c6fed4"
node_id: prepare_packet
checkpoint: PH12.17
kind: bug
summary: Fresh-home property-tax flow stops at the owner input approval because its edge to packet preparation has no yes label; the protected acceptance command also cannot find a checkout root in the isolated run.
evidence: evidence/backlog2/C-PROPERTY-TAX-FLOW-TESTER/RESULTS.md
attempts_made: 0
status: filed
assigned_to: integrator
resolution: ""
resolution_evidence: ""
---

After C-FLOW-ASSET-STAGING commit `4d67657c6f262e46030ace293d3aeb61e9f43124` was confirmed integrated, a fresh real FastAPI/DBOS home installed all four property-tax flows and staged the runtime script in the flow workspace. The public-row-only case used PIN `01011000020000` from the captured 2026 Cook County Assessor Socrata sample; no customer documents were supplied.

Run `852c69c6fed4` approved the local `owner_input_ready` test gate, then failed with `prepare_packet` skipped. The registered edge `owner_input_ready` → `prepare_packet` is unlabeled, and this runtime routes approval output only over a matching `yes` edge. The protected acceptance command failed too: its fallback selected another worker's `.../ventures/property-tax/scripts/property_tax.py` file and ran `cd` on that file. No packet was written, so packet uncertainty handling remains unverified by this run.

See the linked card results and `environment.json` for registered flow details. No portal/account access or external effects occurred. The integrator should repair the flow route and make the protected acceptance command compatible with the staged isolated workspace, then rerun the acceptance from a fresh home.
