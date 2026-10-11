# Property tax appeals proof

## Drift check

- **Checkpoint:** PH12.17, Property tax appeals.
- **Dependencies:** PH5 and PH9 remain `in_progress`, not at exit. PH12 is owner-approved to start in NORTHSTAR.yaml, so this card proceeds; PH12.17 cannot be marked done here.
- **Defining properties and metrics:** P-VERIFY/M-VERIFIED (page citations, uncertainty handling, and independent checks); P-CONTROL (homeowner signs/files; live mailing and checkout remain disabled); P-USABLE (two customer steps, packet plus plain-language filing guide).
- **Existing tools:** uses the existing reader, feed, mail, and venture flow blocks. The addition is venture-specific guide generation; it adds no new dependency or shared block.
- **Acceptance test, written first:** `ventures/property-tax/tests/test_self_file_guide.py::test_packet_includes_homeowner_self_file_guide_and_keeps_filing_manual` verifies the `homeowner_self_file` mode, official portal/calendar links, manual signature/submission wording, and `filing_submitted: false`. The pre-change run failed because the mode was absent.

## Checks run

Checks are listed here only after they have run in this worktree. The venture pytest command covers both fixture behavior and the new self-file guide. Existing live evidence below comes from earlier probes and is not presented as a live end-to-end filing.

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/property-tax/tests/acceptance/test_v_proptax2.py -q --runxfail` — **2 passed**. This includes the previously outstanding homeowner-mode check, which confirms the packet flow itself describes the homeowner self-file guide and leaves filing with the homeowner.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/property-tax -q` — **7 passed, 2 xpassed**. The xpasses are the two `V-PROPTAX2` acceptance checks; their `xfail` marks remain unchanged.
- `git diff --check` — passed.

## Current release-gate findings (2026-10-10)

- Verified the official links used by this venture against Cook County Assessor and Board of Review pages. The Assessor's 2026 rules point pro se taxpayers to SmartFile, allow filing without an attorney at the Assessor, and require filing by the applicable township closing date. The current Assessor calendar lists separate Assessor and Board of Review windows. The Board's Rule 1 allows an individual taxpayer to represent property titled in their own name and requires attorney representation for entities; its residential page states the same limit. The checked links are the rules, calendar, SmartFile, residential appeal pages, and the Board's official rules/residential pages linked from [DECISION.md](DECISION.md). No link change was needed.
- Built [a 50-row public parcel sample](benchmark/cook-county-parcel-sample.json) from the official Cook County Assessor Socrata dataset (`nj4t-kc8j`, tax year 2026), with PIN, year, class, township, ZIP, and source update time only. This is a public-source benchmark sample, not a complete county roll or a valuation benchmark: the source does not include owner mailing addresses, assessed values, or comparable-sale prices.
- The real local Glacier FastAPI/DBOS backend was started in disposable homes with the project venv. Two initial runs (`52bbebcdb9c4`, `b07f55571184`) exposed installer command-binding problems in the protected acceptance command. A regression test reproduced the nested-quote failure; `ventures/install_all.py` now replaces the complete quoted interpreter variable, and the new non-acceptance installer test plus Windows installer checks pass. The next clean install registered all four flows; see [glacier-install-final.log](evidence/glacier-install-final.log).
- Clean run `a3401b49839b` used the 50-row public sample and an intentionally incomplete case (no customer notice or sale documents). It approved the local input gate, then the flow skipped every node after it. In this runtime, approval `yes` branches only follow edges labeled `yes`, but the `owner_input_ready` to `prepare_packet` edge has no label. The protected acceptance command then correctly failed because `packets/case.json` did not exist. Run states, verifier output, and no-external-effects record are in [glacier-live-run-final.json](evidence/glacier-live-run-final.json). There is no successful end-to-end packet output yet.
- PH12.17 remains blocked. The flow-edge repair is within the venture card, but this worker has reached the two-attempt repair limit; no acceptance check was changed. The earlier claim `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT` is assigned to the integrator, and the newly observed unlabeled approval edge needs to be added to the integrator's claim work before another clean engine run. Live mailing remains disabled; no postcard, signature request, customer message, payment, or filing was sent.

- The earlier self-file implementation check and suite run are historical; current results are listed above and include the independent `V-PROPTAX2` acceptance checks.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only property-tax --dry-run` — **4 flows validated**.
- Started a fresh real backend at `127.0.0.1:38423` with a disposable `GLACIER_HOME`; `ventures/install_all.py --only property-tax` installed all four flows (`saved: true`). The packet flow was not run: the known runner-root failure has already repeated three times and is tracked in `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT`; repeating it would not be a useful independent check.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures -q` — collection stopped with 3 import errors because `recall-actor` and `utility-audits` expect their local import roots. Running those suites from their own directories passed: `ventures/recall-actor` **10 passed, 1 skipped, 3 subtests passed**; `ventures/utility-audits` **9 passed**. No other venture files were changed; the broad root invocation does not establish every venture suite as green.
- `git diff --check` — passed.
- Live source evidence previously recorded in [property-tax-live-source.json](../../evidence/ventures/property-tax-live-source.json): one Cook County public parcel row fetched and normalized without schema alerts. This is not a complete roll sync.
- Earlier real-data packet smoke evidence is in [property-tax-live-case.json](../../evidence/ventures/property-tax-live-case.json): exit 0, `uncertain — please check`, missing notice/comparables called out, `filing_submitted` false. It predates the self-file guide change and is not evidence of a customer filing.
- Earlier install evidence is in [property-tax-live-glacier.json](../../evidence/ventures/property-tax-live-glacier.json): four flows saved to the local Glacier backend. The subsequent real packet-flow runs failed before script execution due to runner root discovery; runs `229a5a729228`, `98e0ea2c5227`, `a43f0883bc53` are tracked by claim `CLM-2026-10-10-PROPERTY-TAX-LIVE-FLOW-ROOT`. No successful end-to-end Glacier packet run or filing was verified.
- The full 2026 Cook County roll is incomplete: the prior probe staged 50,000 of 1,864,270 rows. No customer notice or comparable-sale packet was available for live verification.

## Scope and owner actions

- Official Assessor and Board of Review sources support individual homeowners filing for themselves; the Board pro se path is limited to an individual taxpayer whose property is titled in their own name. See [DECISION.md](DECISION.md).
- The generated packet includes a distinct `*-filing-guide.md` with current official portal and calendar links. The homeowner checks current dates, resolves uncertainties, chooses the filing stage, signs, submits, and tracks notices.
- Glacier does not create county accounts, pay, sign, submit, or represent the homeowner. Texas stays future-only. Checkout remains disabled until the owner confirms pricing. Live mailing remains disabled; postcards are local render-only proofs.
- This work does not close PH12.17: the full roll, successful real Glacier run, customer-provided documents, and owner launch confirmation are still outstanding.
