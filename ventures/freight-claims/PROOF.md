# Freight claims proof

Checkpoint: PH12.14. Test data in the real-runtime attempt was synthetic and local-only. No ShipStation account was connected, no carrier was contacted, and no claim, invoice, or payment was submitted.

## ShipStation API plan handling and CSV intake (this card)

The shared read-only connector now converts ShipStation HTTP 401/403 responses and plan/permission error bodies into this owner-facing message: “This ShipStation account can't use the API (ShipStation requires the Gold plan or higher). Upload a ShipStation shipments export (CSV) instead.” The connection-check CLI prints the same message; tests verify that a fake API key never appears in the error. No real ShipStation key or account was used.

The local parser accepts Shipments and Orders CSV fixtures with common column-name variants, ignores extra/missing optional columns, maps available shipment/order/address/weight/item/status fields into shipment records, and reports skipped row numbers and reasons. When enabled API reads fail, the daily watch flow uses the newest `.csv` in `incoming/`; an explicit file can be selected with `claims.py watch --csv PATH`. A working API remains preferred. The fixtures contain invented data.

Commands and results:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests/test_csv_intake.py ventures/blocks/connectors/tests/test_connectors.py
# 23 passed

~/w/glacier-lean/.venv/bin/python -m ventures.install_all --dry-run --only freight-claims
# Seven flows validated

~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims ventures/blocks -q --ignore=ventures/blocks/filer/tests/test_filer_acceptance.py
# 81 passed
```

The exact requested combined command was also run:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims ventures/blocks -q
# 80 passed, 3 failed (at the time of this combined run)
```

After that combined run, one more connector fixture case was added for a permission message in an HTTP 200 response. The final focused run is 23 passed and the final run excluding the known filer blocker is 81 passed.

All three failures are existing `ventures/blocks/filer/tests/test_filer_acceptance.py` cases. They stop before exercising the filer because Node cannot resolve its Playwright dependency (`MODULE_NOT_FOUND` from `ventures/blocks/filer/runner.mjs`). This is recorded in [the shared-block environment claim](../../vault/claims/2026-10-10-ph12-14-filer-playwright-missing.md); the filer lane and dependencies were not changed. Therefore the complete requested suite is not green yet.

All results above are fixture/local-only proof. No live ShipStation account/API plan, real export, live shipment, claim, carrier contact, invoice, or payment was exercised. Live connection and live customer-data checks remain pending.

## Focused acceptance suite

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests/test_claims.py
```

Result: `14 passed in 0.12s`.

The tests cover damaged-item invoice totals and customer confirmation, evidence requirements, insurance consent, customer confirmation of carrier terms, one-time 30/120-day reminders, customer-provided carrier receipt confirmation, contingency invoice arithmetic, read-only tracking opt-in and exception classification, loopback-only filer use, and delegation to the shared customer signature block.

## Local end-to-end packet preparation

Command:

```sh
mkdir -p /tmp/freight-claims-proof
GLACIER_HOME=/tmp/freight-claims-proof GLACIER_READER_MODEL_TIMEOUT=1 ~/w/glacier-lean/.venv/bin/python ventures/freight-claims/scripts/claims.py prepare --input ventures/freight-claims/tests/fixtures/demo-intake.json --output-dir /tmp/freight-claims-proof/packets
```

Result: `match`; recipient `claims@carrier.example.test`; claimed damaged-item invoice value `$250.00`; carrier liability estimate `$200.00`; four supporting files; `email_sent: false`; no side effects. Inputs and the carrier terms URL in `tests/fixtures/demo-intake.json` are synthetic, local-only test values.

## Flow validation and registration

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.install_all --dry-run --only freight-claims
```

Result: all six flows validated: `freight-watch-shipstation`, `freight-check-deadlines`, `freight-request-authorization`, `freight-prepare-claim`, `freight-record-carrier-receipt`, and `freight-invoice-draft`.

Command:

```sh
GLACIER_HOME=/tmp/glacier-live-Dk68RB GLACIER_API=http://127.0.0.1:45109 ~/w/glacier-lean/.venv/bin/python -m ventures.install_all --only freight-claims
```

Result: all six flows saved through the real Glacier HTTP API. The prepare flow run `fe2f22f5fdc0` failed before executing its command because the runner used the literal working directory `/tmp/glacier-live-Dk68RB/workspaces/freight-prepare-claim/{repo}`. The same blocker is tracked in [CLM-PH12-20-CWD-REPO](../../vault/claims/2026-10-10-ph12-20-command-cwd-repo-placeholder.md); this venture did not change platform code. The failed run had no external side effects.

No screenshot was captured. The requested Playwright capture remained queued because both shared heavy-job slots were occupied, and the flow itself stopped before its command output appeared. The full real-flow acceptance remains pending the platform fix.

## Remaining real-data checks

- Owner adds a ShipStation read-only key and explicitly enables polling after reviewing the account plan's API quota.
- Owner reviews the first ShipStation listing and the first ten claim packets.
- Run the real flow with customer-provided bills of lading, invoices, delivery receipts, damage photos, carrier terms, and a confirmed carrier receipt date.
- After the platform runtime claim is resolved, rerun the flow in real Glacier and capture its successful packet and approval gate.
- The shared venture lane does not currently provide a customer-facing document upload link; this build uses the local incoming folder until PH12.2 supplies an approved upload path.
- Contingency charges are calculated as an invoice draft only. No customer payment link is created or charge processed.
