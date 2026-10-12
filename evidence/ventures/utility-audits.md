# Utility audits evidence

## Focused acceptance tests

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s ventures/utility-audits/tests -v
```

Result: **Ran 7 tests in 0.001s — OK.** Cases cover customer-confirmed statewide threshold totals, an ineligible ratio, missing/multiple-meter uncertainty, malformed and nonconsecutive periods, invalid invoice tax, estimate math, a flat-rate scenario, and unsigned/unsubmitted draft state.

## Manifest and flow validation

Command:

```sh
/home/glacier/w/glacier-lean/.venv/bin/python -m ventures.install_all --only utility-audits --dry-run
```

Result:

```json
[{"venture":"utility-audits","flow":"utility-audit-calculator","validated":true}]
```

## Local CLI dry-run

Input: synthetic 12-month records in `ventures/utility-audits/tests/sample_audit.json`, copied to a disposable `GLACIER_HOME`.

Output: `result: match`, statewide tax year `2025`, estimated future annual exemption savings `240.0 USD`, customer-entered rate comparison savings `1080.0 USD` (availability uncertain), ST-200R field draft present, `signed: false`, `submitted: false`.

No real restaurant bills or tariff sources were available. The real Glacier check did not start: `heavy npm run live` waited 15m09s for a shared heavy-job slot and was canceled per the project backstop; see `vault/claims/2026-10-10-v-utility-live-lock.md`. The live flow must pause at its Indiana owner-confirmation gate. No screenshot was captured because the app never started. Independent reviews confirmed the statewide-scope and month-validation fixes, rate scenario math/safety limits, and consistency between the manifest scope and flow prompt.
