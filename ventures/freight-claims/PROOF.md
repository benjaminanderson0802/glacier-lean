# Freight claims proof

Checkpoint: PH12.14. Test data in the real-runtime attempt was synthetic and local-only. No ShipStation account was connected, no carrier was contacted, and no claim, invoice, or payment was submitted.

## Focused acceptance suite

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests/test_claims.py
```

Result: `14 passed in 0.37s`.

The tests cover damaged-item invoice totals and customer confirmation, evidence requirements, insurance consent, customer confirmation of carrier terms, one-time 30/120-day reminders, customer-provided carrier receipt confirmation, contingency invoice arithmetic, read-only tracking opt-in and exception classification, loopback-only filer use, and delegation to the shared customer signature block.

## Local end-to-end packet preparation

Command:

```sh
GLACIER_HOME=/tmp/glacier-live-Dk68RB GLACIER_READER_MODEL_TIMEOUT=1 ~/w/glacier-lean/.venv/bin/python ventures/freight-claims/scripts/claims.py prepare --input /tmp/glacier-live-Dk68RB/ventures/freight-claims/incoming/claim-intake.json --output-dir /tmp/glacier-live-Dk68RB/ventures/freight-claims/manual-packets
```

Result: `match`; claimed damaged-item invoice value `$250.00`; carrier liability estimate `$200.00`; one each of delivery receipt, photo evidence note, commercial invoice, and bill of lading; `email_sent: false`; no side effects. All inputs and the terms URL were synthetic, local-only test values.

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
