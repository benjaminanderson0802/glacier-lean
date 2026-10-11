# Freight claims proof

## Release-gate update (2026-10-10)

The missing CSV-to-packet engine path is now wired: `freight-prepare-claim` runs the existing `prepare-csv` command against `incoming/shipstation-shipments.csv` plus separate customer-confirmed intake. The run still pauses at `owner_input_ready` until the required data is supplied and approved. A temporary fixture-only copy of the installed flow omitted interactive approval and owner-review nodes so its processing path and unchanged acceptance command could be exercised without impersonating the owner.

The venture was installed through the real local Glacier API into an isolated `GLACIER_HOME`. The fixture runs and artifacts are recorded in [the Glacier run bundle](evidence/glacier-engine-runs.json), [the run log](evidence/glacier-run-log.md), and the adjacent packet, candidate, receipt, and deadline JSON files.

| Glacier run | Result |
| --- | --- |
| `3336faf13477` — `freight-watch-shipstation` | `done`, verified; read the synthetic CSV and identified one possible UPS damage exception. |
| `fbaf166507d9` — production `freight-prepare-claim` | Waiting at `owner_input_ready`; production approval gates were preserved. |
| `bf91121187a4` — fixture-only packet-processing flow | `done`, verified; joined one exception to the separate intake and generated a source-linked packet with a 2026-12-08 estimated deadline, `$250.00` confirmed damaged-item value, no missing documents, `sent: false`, and no side effects. The unchanged Glacier acceptance check passed. |
| `75f3f083fa79` — `freight-record-carrier-receipt` | `done`, verified; recorded the synthetic receipt fixture and created 30/120-day reminders. |
| `75fe4386da35` — `freight-check-deadlines` | `done`, verified; found the synthetic 30-day follow-up due on 2026-10-10. |

All shipment, intake, document, and carrier-receipt data in these runs are synthetic fixtures. No ShipStation account or live export was used, and no carrier was contacted, claim filed, message sent, payment made, or signature collected. The successful processing-only flow is explicitly a test copy; the production flow waits at its owner approval node as intended.

### Carrier source verification

The nine carrier-source links used by the packet templates were checked on 2026-10-10. UPS, FedEx, USPS, Postal Explorer, and the U.S. Government Publishing Office pages returned HTTP 200 and official content. The three eCFR sections returned the official section text through the documentation browser; direct `urllib` requests in this environment reached a Federal Register anti-bot interstitial. The former House Office of the Law Revision Counsel URL was under maintenance, so the LTL materials now link to the official GPO 2024 edition of 49 U.S.C. § 14706. Link-by-link observations are in [carrier-source-verification.json](evidence/carrier-source-verification.json). This is source-link and page-content verification, not a legal opinion or a service-specific deadline determination.

The official pages support the template distinctions: UPS uses scheduled delivery for its 60-day claim window; FedEx parcel windows use shipment date and distinguish domestic, international, and lost shipments; USPS lost-mail windows vary by mail class; the Carmack statute and 49 CFR response periods apply only when governing conditions are met. Recheck a carrier's exact service terms and shipment facts before relying on an estimated date.

Validation after the flow and source-link changes:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.install_all --dry-run --only freight-claims
# all seven flows validated
~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims -q
# 35 passed
~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q
# 21 passed
```

Venture status is `ready` for owner setup and review. The first ShipStation listing, account connection or CSV provision, review of the first ten distinct packets, shipper authorization/signature/filing and customer responses, and any invoice approval remain human steps. No real-data or public-use readiness is claimed.

## Carrier-specific template acceptance (2026-10-10)

Added printable packet checklists for UPS, FedEx, USPS, and LTL/Carmack under `carrier-templates/`. They state the filing window and date anchor, required evidence, source links, and response-date fields. The USPS checklist requires service lookup for lost mail; LTL response reminders are conditional on Part 370 applying. All checklists leave filing and carrier contact with the shipper.

The independent acceptance check originally failed because `carrier-templates/` did not exist. After adding the checklists, this command passed with the xfail marker ignored:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims/tests/acceptance/test_v_freight2.py::test_carrier_specific_packet_templates_cover_deadlines_and_evidence -q --runxfail
# 1 passed
```

The complete venture suite also passed:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/freight-claims -q
# 34 passed, 1 xpassed
```

This checks local template content only. It does not establish live carrier service terms, claim filing, or response behavior. The sources linked in the templates should be rechecked for each shipment before a shipper relies on a deadline.

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

Official guidance cited by the templates: [UPS filing window](https://www.ups.com/us/en/support/file-a-claim) and [UPS evidence list](https://www.ups.com/us/en/support/file-a-claim/supporting-documents); [FedEx deadlines and evidence](https://www.fedex.com/en-us/customer-support/claims.html); [USPS claims and evidence](https://faq.usps.com/articles/Knowledge/Domestic-Claims-The-Basics) and [Domestic Mail Manual 609](https://pe.usps.com/TEXT/DMM300/609.htm); [49 U.S.C. § 14706 (GPO 2024 edition)](https://www.govinfo.gov/content/pkg/USCODE-2024-title49/html/USCODE-2024-title49-subtitleIV-partB-chap147-sec14706.htm), [49 CFR § 370.3](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.3), [§ 370.5](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.5), and [§ 370.9](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.9).

No real ShipStation account, carrier claim, filing, payment, signature, invoice, or carrier response was exercised. These artifacts establish fixture behavior only, not live launch readiness.

Historical UI/backend startup check: from `glacier/web`, `npm run live` successfully started the disposable FastAPI backend, which answered `GET /api/health` with HTTP 200. The combined live script then stopped because this worktree's untracked `glacier/web/node_modules` does not contain `vite/bin/vite.js` (`MODULE_NOT_FOUND`); it cleaned up its own backend process and temporary home. This did not block the current headless Glacier-engine run documented above; UI startup remains outside this freight card's `ventures/**` file scope.

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

Historical attempt: six flows were saved through the real Glacier HTTP API. The prepare flow run `fe2f22f5fdc0` failed before executing its command because that installer version left `{repo}` in the working directory. The installer now binds the checkout path and Python executable; the current fixture processing run completed and verified as recorded above. The historical failed run had no external side effects.

No screenshot was captured. The requested Playwright capture remained queued because both shared heavy-job slots were occupied. The production prepare flow currently pauses at its `owner_input_ready` approval; the successful processing-only fixture copy above tests packet generation without bypassing the production owner step.

## Owner/customer data still needed for live use

- Owner adds a ShipStation read-only key and explicitly enables polling after reviewing the account plan's API quota.
- Owner reviews the first ShipStation listing and the first ten claim packets.
- Provide customer shipment data and actual bills of lading, invoices, delivery receipts, damage photos, carrier terms, and carrier receipt dates before using the flow for a real claim.
- The shared venture lane does not currently provide a customer-facing document upload link; this build uses the local incoming folder until PH12.2 supplies an approved upload path.
- Contingency charges are calculated as an invoice draft only. No customer payment link is created or charge processed.
