# Progress — Carpenter's goods

## Drift check

- Checkpoint: PH12.20. PH5 and PH9 are marked at exit in `NORTHSTAR.yaml`.
- Defining properties and metrics: P-USABLE / M-INTERVENE for a clear owner step; P-VERIFY / M-VERIFIED for checked listing output and paid-only commission calculations.
- Existing tools: the venture's CSV CLI and local Glacier engine cover the workflow; the project interpreter and standard-library CSV support are used. No new dependency was added.
- Acceptance: the unchanged venture suite plus non-acceptance regression checks for approval routing and the public Shopify export layout; live engine proof records the command/output check and owner-review wait.

## Work and evidence

Fixed the listing flow's `owner_input_ready → prepare_draft` edge to use the approval node's `yes` branch. Added `tests/test_flow_runtime.py`; it failed before the flow fix and passes now. A disposable real engine run installed both flows and exercised listing run `c2b14bf4f01f`. The synthetic input approval resumed the graph; `prepare_draft` and `draft_ready` completed, outputting an unpublished Etsy/Shopify draft and passing the required output check. The run is still waiting for the owner to review the draft. The owner approval was not simulated.

Verified official Etsy and Shopify CSV export instructions. Shopify's official order export documentation says multi-item orders occupy multiple CSV lines and order-level fields may be blank on continuation lines. Added grouping for this shape and a public-schema benchmark test with synthetic values in `tests/test_official_export_benchmark.py`; its red test passed after the importer change. No public merchant records or real merchant export were used. No official public current completed-sale source was identified; three current source-linked comparable sales still need to come from the owner/maker.

The commission flow installs but the live engine refuses to start it because it has no completion check. I-04 prevents this worker from authoring the check that judges this flow; an independent check author is needed. Therefore PH12.20 is still unverified and the venture stays **blocked**. The owner step and current gate status are recorded in `README.md`, `PROOF.md`, and `../OWNER-START-HERE.md`.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods -q` — **14 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/carpenter-goods/tests/test_flow_runtime.py ventures/carpenter-goods/tests/test_official_export_benchmark.py -q` — **2 passed**.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run` — both flows validated.
- Real Glacier engine evidence and the commission-flow refusal are recorded in `PROOF.md`.

## Anti-pattern check

The prior proof treated a stale `waiting` read as a completed runtime result. The fresh smoke waits for a terminal or next approval state and records that the listing command and output check completed while the run awaits owner review. The commission limitation is left visible rather than hidden behind a self-authored check.
