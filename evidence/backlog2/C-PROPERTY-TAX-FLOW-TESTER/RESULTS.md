# C-PROPERTY-TAX-FLOW-TESTER — real-backend run

## Result

**Acceptance not met.** The fresh-home real-backend run did not reach packet preparation, so this run cannot confirm a dated source result inside a packet or verify the expected missing-evidence uncertainty.

## Run setup

- Checkpoints: PH12.17 and PH12.22; PH12 parallel authorization applies.
- C-FLOW-ASSET-STAGING prerequisite: integrated. Commit `4d67657c6f262e46030ace293d3aeb61e9f43124` is an ancestor of `origin/glacier-final` at `809cf3d1e8e9bc409aadef26d2b8f4dacf35addf`.
- Backend: real local FastAPI/DBOS at `http://127.0.0.1:38571`.
- Disposable home: `/tmp/glacier-pt-flow-tester-20261011T170613Z`.
- Project interpreter: `/home/glacier/w/glacier-lean/.venv/bin/python`.
- Feed input: 50 rows from the captured Cook County Assessor Parcel Universe public Socrata sample; the smoke row is PIN `01011000020000`, tax year `2026.0`, Barrington, source updated `2026-10-01T14:09:41.080Z`, captured feed fetch time `2026-10-11T02:46:39+00:00`. Source normalization reported no alerts. The sample omits values and sales data.
- Case input: the public PIN only; no notice or comparable-sales documents were supplied.
- Install: all four property-tax flows registered successfully (`saved: true`). The flow script was staged under the isolated flow workspace.

## Flow outcome

- Run ID: `852c69c6fed4`.
- The local `owner_input_ready` test gate was approved to exercise the flow.
- Final state: `failed`; `owner_input_ready` was `done`, while `prepare_packet`, `packet_ready`, review, and note nodes were `skipped`.
- The registered edge from `owner_input_ready` to `prepare_packet` has no label. The runtime routes approval output over a matching `yes` edge, so packet preparation was skipped.
- The required protected acceptance command also failed before inspecting a packet: its fallback found another worker's `property_tax.py` file and attempted to `cd` into that file.
- No packet file was produced. Therefore this run does not establish packet uncertainty handling or a successful verified run.

## Side-effect boundary

No portal was opened, no account was accessed, no customer file was used, and no signature, message, mailing, payment, or filing was made. The only approval was the local input gate for this synthetic public-row case. Packet handoff was never reached.

## Artifacts

- `plan.md` — acceptance-first plan and drift check.
- `source-seed.json` — public-source row and fetch provenance staged in the disposable home.
- `install.json` — four real-backend flow install results.
- `environment.json` — registered runtime flow, including the unlabeled edge and staged script presence.
- `run.json` and `run-final.json` — run start, approval, final API state, node states, and acceptance failure.
- Claim: `vault/claims/2026-10-11-property-tax-flow-tester-run-blocked.md`.
