# Property tax appeals progress

PH12.17 implementation remains in progress. Launch stays disabled until the owner resolves the Venture Build Spec/Assessor representation-rule discrepancy and confirms Cook County packet-only scope. Texas registration is labeled as a future expansion step, not part of Cook County launch. The exact postcard proof directory and `approve_proof` review step are linked from the owner instructions.

The shared feed block now downloads the latest Cook County tax year in resumable 10,000-row pages, with at most five pages per sync. The sync reports downloaded/total counts and keeps the previous complete snapshot active until all pages arrive. Live probe on 2026-10-10 found tax year 2026 with 1,864,270 source rows and staged 50,000; progress is visible and the roll is not yet complete. No current customer notice or comparable-sale packet was available.

`/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/property-tax/tests` — 6 passed. Full Glacier packet-flow run and owner launch confirmation remain outstanding; see claim `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT`.
