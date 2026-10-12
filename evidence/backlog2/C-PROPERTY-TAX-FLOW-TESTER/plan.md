# C-PROPERTY-TAX-FLOW-TESTER — acceptance plan

## Acceptance test (written first)

From an isolated Glacier home, install the current property-tax flows, run the Cook County public-row smoke case through the real backend, and capture a run that reaches packet preparation with the dated public source result. Since customer notice and comparable-sale evidence are absent, the packet must preserve the expected uncertainty, identify missing evidence, and remain not filed / not filing-ready. No customer parcel file, portal navigation, account login, signature, message, mailing, or filing is in scope.

## Drift check

- **Checkpoint:** PH12.17 (property-tax appeals) and PH12.22 (integration/independent audit), as explicitly authorized in parallel by the card.
- **Dependencies:** PH12 is owner-approved for parallel work; the sole card dependency, C-FLOW-ASSET-STAGING, is integrated. Commit `4d67657c6f262e46030ace293d3aeb61e9f43124` is an ancestor of `origin/glacier-final` (`809cf3d1e8e9bc409aadef26d2b8f4dacf35addf`), and the integrated `ventures/install_all.py` stages runtime assets into flow workspaces.
- **Properties / metrics:** P-VERIFY and P-CONTROL; M-VERIFIED and M-AUDIT.
- **Existing tools:** use the installed property-tax flow, `ventures/install_all.py`, and Glacier's real FastAPI/DBOS backend. No new runner is needed.
- **Acceptance test:** stated above before execution. This task adds no tests and edits no judging tests or flow/platform/packet code.

## Evidence to capture

Record the disposable home, unique backend URL, install result, run ID, node states, packet JSON and readable packet output, dated public-source provenance, missing-evidence uncertainty, and explicit absence of external effects. Keep all task artifacts in this directory.
