# Warranty registration progress

## Drift check

1. Checkpoint: PH12.11, Warranty registration.
2. Dependencies: PH5 and PH9 have not reached their exits. PH12 is owner-approved and the card explicitly authorizes work in wave 6, so this venture can start; this card cannot mark PH12 or its exits complete.
3. Defining properties and metrics: P-GOALS (turn a contractor's recurring install intake into a flow), P-CONTROL / M-AUDIT (read-only Jobber and approvals before future sends or filings), P-VERIFY / M-VERIFIED (independent readings and deterministic checks), and P-USABLE / M-TTFA (three plain-language owner steps).
4. Existing tools: use the existing read-only Jobber connector and shared portal filer. No new dependency is added. The reader and deadline tracker packages named by the spec are not present in this checkout; the connector's current job result omits completion and customer/unit fields, so real intake cannot yet be completed in this lane.
5. Acceptance test written first: `ventures/warranty/tests/test_warranty.py` covers brand windows, regional exceptions, input agreement, missing photo opt-in, deadlines, and duplicate prevention. Release evidence also requires venture installer validation, the shared filer mock check, and a dry run in real Glacier.

Implemented the warranty manifest, two scheduled Glacier flows, conservative intake/deadline checks, a read-only Jobber connector entry point, and a local-only adapter to the shared portal filer. Brand submission remains disabled: Daikin's terms prohibit automation; the other four brands lack clear public authorization; verified brand serial-format rules are also missing. The shared deadline tracker and document reader packages are not present in this checkout, and the Jobber connector currently exposes only job id, job number, and title, so real completed-install intake is not yet possible.

Focused acceptance tests pass (15 passed); connector fixture check passes (11 passed); venture installer dry-run validates all three flows. A live Glacier run reached the deadline review approval with a synthetic three-day deadline alert and no external action; run metadata is saved under `evidence/ventures/warranty/`. The screenshot and shared filer mock release check are pending. No checkpoint status was changed.
