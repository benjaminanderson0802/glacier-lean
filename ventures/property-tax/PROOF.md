# Property tax appeals proof

## Drift check

- **Checkpoint:** PH12.17, Property tax appeals.
- **Dependencies:** PH5 and PH9 remain `in_progress`, not at exit. PH12 is owner-approved to start, so this card proceeds; PH12.17 cannot be marked done here.
- **Defining properties and metrics:** P-GOALS/P-CONTROL and M-INTERVENE: Glacier prepares the packet, while the owner confirms scope once and the homeowner reviews, signs, and files each appeal. P-VERIFY/M-VERIFIED: the protected post-run check must pass on a real Glacier engine run.
- **Existing tools:** uses Glacier's existing approval nodes, flow runner, feeds, and packet script. No dependency or shared block was added.
- **Acceptance test, written first:** the existing protected acceptance command in `property-tax-prepare-packet.json` must pass after the actual packet node runs; `ventures/property-tax/tests/acceptance/test_v_proptax2.py` remains untouched. A new non-acceptance regression, `test_packet_input_approval_routes_to_preparation_on_yes`, checks the labeled edge.

## Flow fix

The `owner_input_ready` approval now routes to `prepare_packet` on `yes`. The branch is explicit because Glacier approval nodes follow only edges whose labels match their `yes` or `no` result. The new unit regression failed before the label existed (`KeyError: 'label'`) and passes with `label: "yes"`.

## Public sample and limits

The checked-in [50-row sample](benchmark/cook-county-parcel-sample.json) comes from the official Cook County Assessor Socrata dataset `nj4t-kc8j`, tax year 2026. It contains PIN, year, class, township, ZIP, and source update time only; it is not a complete roll and has no owner address, assessment value, or sale prices. Its first PIN is `01011000020000`. The official Assessor and Board portal sequences in [OWNER-STEPS.md](OWNER-STEPS.md) were checked against their pages on 2026-10-11. See the [Assessor filing page](https://www.cookcountyassessoril.gov/online-appeals), [current calendar](https://www.cookcountyassessoril.gov/assessment-calendar-and-deadlines), and [Board property-owner portal guide](https://www.cookcountyboardofreview.com/portal-guide-property-owners).

## Checks

- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only property-tax --dry-run` — **4 flows validated**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/property-tax -q --runxfail` — **49 passed**, including the unchanged V-PROPTAX2 acceptance checks and the new approval-edge regression.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` — **24 passed, 2 subtests passed**.
- The first full venture-suite run exposed a date-sensitive existing test and an expectation mismatch in the edited manifest test. The date test now supplies its fixed `on_date` explicitly; neither the acceptance checks nor their expectations were modified.
- `git diff --check` — passed.

## Real engine rerun: blocked

The prior live run `a3401b49839b` proved the original defect: after approving `owner_input_ready`, `prepare_packet` was skipped because the edge had no label; the protected check failed because no packet existed. Its untouched record is [glacier-live-run-final.json](evidence/glacier-live-run-final.json).

This card fixed that edge, but a fresh real-engine proof did not complete. Attempt 1 stopped before engine startup because sample normalization used the default `GLACIER_HOME`; it was discarded. Attempt 2 used a fresh temporary home and staged all 50 rows with no schema alerts. The proof runner made one API request immediately after launching Uvicorn, without waiting for readiness; it got `Connection refused`, then terminated the child in cleanup. The empty backend log does not establish whether startup would have succeeded. The attempt record and log are [glacier-live-run-2026-10-11.json](evidence/glacier-live-run-2026-10-11.json) and [glacier-live-backend-2026-10-11.log](evidence/glacier-live-backend-2026-10-11.log). Claim [CLM-2026-10-11-PROPERTY-TAX-REAL-ENGINE-STARTUP](../../vault/claims/2026-10-11-property-tax-real-engine-startup.md) records the harness error. No further attempts were made.

Therefore the 50-row **real Glacier engine run and protected acceptance pass are not claimed**, and the manifest/portfolio status stays `blocked`. No external effects occurred. The case used only public parcel metadata; no notice or comparable documents were present, so it cannot support a valuation conclusion or customer filing.

## Owner steps

The manifest now has one one-time owner step: confirm the Cook County individual-homeowner self-file scope. For each appeal, the homeowner reviews the generated packet, resolves uncertainties, signs, and files personally. [OWNER-STEPS.md](OWNER-STEPS.md) gives portal links, current clicks, values to copy from that case's generated files, and time estimates. Pricing stays owner-controlled; paid checkout and live mailing remain disabled.
