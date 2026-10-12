# Property tax appeals progress

PH12.17 remains blocked pending a fresh real Glacier engine run. The reported flow defect is fixed: `owner_input_ready` now routes `yes` to `prepare_packet`, and a new venture unit regression covers that branch. The existing protected acceptance command and all files under `tests/acceptance/` remain unchanged.

The 2026 Cook County Assessor Socrata sample contains 50 public parcel-metadata rows; it is not the full county roll and does not contain notices, owner addresses, assessed values, or sale prices. The fresh proof runner staged all 50 rows but checked the API immediately after launching Uvicorn, then stopped the child on `Connection refused` rather than polling for readiness. No real packet output or protected-check pass is claimed for this task; the exact attempt and claim are linked from [PROOF.md](PROOF.md).

The owner workload is reduced to confirming Cook County individual-homeowner self-file scope once, then reviewing, signing, and filing each appeal personally. Exact portal instructions, case-specific copy values, and time estimates are in [OWNER-STEPS.md](OWNER-STEPS.md). Paid checkout and live mailing remain disabled. The current official source links and filing steps were checked on 2026-10-11.
