# Freight claims proof

## Carrier packet templates and CSV-to-packet acceptance (2026-10-10)

Added venture-local guidance for UPS, FedEx, USPS, and LTL/Carmack review. Each generated packet includes a filing-window note, chosen date anchor and calculated estimate when enough dates exist, carrier-specific evidence checklist, official source links, and a response-tracking record. UPS, FedEx, and USPS timelines are scoped to the published package/service rules; USPS lost-mail deadlines remain service-specific. For LTL, the nine-month date is only the Carmack statutory minimum when it applies, and carrier response milestones are labeled as 49 CFR Part 370 reminders only when that part governs. Parcel response dates are not presented as carrier promises. The owner/customer records the actual carrier receipt and any promised response date; no carrier form is sent.

The new `prepare-csv` command joins exception shipments in a local ShipStation CSV to a separate customer-confirmed intake record and prepares source-linked packet drafts. CSV rows alone never assert a loss, damage, amount, or evidence. Missing intake stays in `needs_customer_intake`. The customer-facing questions and evidence list are in [CUSTOMER-INTAKE.md](incoming/CUSTOMER-INTAKE.md). The first ten distinct packets still require Glacier owner approval; the shipper still signs and files each claim and decides settlements.

Acceptance command and result:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims -q
# 31 passed
```

`test_shipstation_csv_fixture_to_carrier_claim_packets` joined a synthetic UPS exception row to separate customer-confirmed claim details and produced a JSON packet with its `$125.00` claimed value, estimated 60-day deadline (2026-03-06 from the fixture's scheduled-delivery date), attached evidence, `sent: false`, and no side effects. This is fixture-only evidence; no real carrier response or filing was made.

The broad collection command `~/w/glacier-lean/.venv/bin/python -m pytest ventures -q` did not collect three unrelated test modules from the repo root: two recall-actor imports fail on `src.sources`, and utility-audits import fails on `scripts.utility_audit`. Running venture test directories with `PYTHONPATH` set to the repo root resolves those collection-only issues. That per-venture run passed Apify, all shared blocks except filer, Carpenter goods, co-op, CPSC, DIBBS, FDA, OSHA, property tax, recall actor, utility audits, warranty, and the freight suite. Existing unrelated failures remain: `ventures/tests/test_install_all.py` assumes only two flows (`36 != 2`), three filer acceptance tests cannot resolve Playwright (`MODULE_NOT_FOUND`), and recall-checker has one source-vocabulary assertion mismatch (`no match found` vs `no match`). These files are outside the freight card and were not changed.

Official guidance cited by the templates: [UPS filing window](https://www.ups.com/us/en/support/file-a-claim) and [UPS evidence list](https://www.ups.com/us/en/support/file-a-claim/supporting-documents); [FedEx deadlines and evidence](https://www.fedex.com/en-us/customer-support/claims.html); [USPS claims and evidence](https://faq.usps.com/articles/Knowledge/Domestic-Claims-The-Basics) and [Domestic Mail Manual 609](https://pe.usps.com/TEXT/DMM300/609.htm); [49 U.S.C. § 14706](https://uscode.house.gov/view.xhtml?edition=prelim&num=0&req=granuleid%3AUSC-prelim-title49-section14706), [49 CFR § 370.3](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.3), [§ 370.5](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.5), and [§ 370.9](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.9).

No real ShipStation account, carrier claim, filing, payment, signature, invoice, or carrier response was exercised. These artifacts establish fixture behavior only, not live launch readiness.

Real backend startup check: from `glacier/web`, `npm run live` successfully started the disposable FastAPI backend, which answered `GET /api/health` with HTTP 200. The combined live script then stopped because this worktree's untracked `glacier/web/node_modules` does not contain `vite/bin/vite.js` (`MODULE_NOT_FOUND`); it cleaned up its own backend process and temporary home. No UI or real flow run was performed. This is an environment dependency issue outside the freight card's `ventures/**` file scope.

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
