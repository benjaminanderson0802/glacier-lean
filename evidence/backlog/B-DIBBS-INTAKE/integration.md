# DIBBS intake merge integration evidence

## Drift check

- Checkpoint: PH12.19. PH12 depends on PH5 and PH9, which remain in progress; the backlog ledger explicitly authorizes this scoped work in parallel. This records no phase exit.
- Properties and metrics: P-VERIFY and P-CONTROL; M-VERIFIED and M-AUDIT.
- Existing tools: the existing JSON parser, SHA-256, CSV writer, pytest suite, and Glacier runtime cover the task. No dependency or external service was added.
- Acceptance: changed part, quantity, supplier, or quote revision cannot reuse an old confirmation; verified records produce traceable unsigned CSV; feed alerts remain visible even when an unverified solicitation yields no bid row.

## Reproduction and correction

After merging the intake implementation, the DIBBS suite reproduced both reported failures: 2 failed, 26 passed. The legacy batch fixture had no owner-confirmed source records. The feed test's confirmed input was also modified with discovery-only description metadata before validation, which invalidated its confirmation digest.

Builder-owned unit fixtures now include synthetic source files, matching hashes, acquisition dates, and owner confirmations. The feed helper preserves the confirmed owner record instead of enriching it with discovery fields. An additional unit case confirms an unverified solicitation remains unranked while its feed alert appears both in the return value and saved bid-sheet JSON.

## Verification

- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/dibbs-supply/tests` — 29 passed.
- `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/tests` — 22 passed.
- `git diff --check` — passed.
- Real local Glacier backend: installed the DIBBS flows into disposable `GLACIER_HOME=/tmp/gf-M-DIBBS-live-20261011`, started the daily prep flow as run `145b59258024`, and approved only its synthetic empty-input gate. The flow completed with `uncertain — please check`, `submitted: false`, and `live_source_checked: false`. No SAM.gov request or external action occurred; this verifies fixture-through-engine behavior only.

The real SAM.gov key canary, current solicitation records, and actual supplier quotes remain owner-dependent and were not tested.
