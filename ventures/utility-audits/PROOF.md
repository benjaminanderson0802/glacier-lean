# Utility audits proof

## PH12.18 release-gate update — 2026-10-10

The venture is **ready for owner action**. The non-owner release gates are cleared below; it is not a claim that a customer case has been approved or filed.

### Real Glacier engine run

Installed both manifest flows into an isolated temporary `GLACIER_HOME` and ran `utility-predominant-use` through the real FastAPI/DBOS engine. The run read the checked-in synthetic 12-month CSV, ran the venture command, passed the flow's `draft_ready` check, and wrote unsigned ST-200 application data. Run `c878d6046ac4` returned a 64.00% screen, `$840.00` future exemption estimate after DOR approval, `signed: false`, and `submitted: false`. An initial approval API request arrived before the engine had persisted its waiting state and returned 409; after polling until `waiting_on=confirm_state`, the same approval succeeded. The engine run remains waiting at the final owner review approval, so it is **not** recorded as a completed or verified end-to-end filing.

For this isolated verification only, the disposable installed flow's first approval prompt was temporarily changed to say that it authorizes the synthetic fixture run and does not confirm Indiana as the launch state. The committed flow is unchanged. The run artifact, API outputs, draft, and step log are in [`evidence/engine-run-2026-10-10.json`](evidence/engine-run-2026-10-10.json) and [`evidence/engine-run-2026-10-10.log`](evidence/engine-run-2026-10-10.log). No customer data, external contact, signing, payment, account creation, or filing occurred.

### Official-source benchmark

Bulletin #55 states that the 100% utility exemption requires **more than 50%** exempt use and that each meter is tested separately (p. 3). A rule-boundary benchmark derived from that official public rule covers 49.99%, 50.00%, 50.01%, and the existing 64.00% fixture. All four outcomes matched the rule in the venture's CSV estimator. The numeric inputs are constructed test values, not official customer records or a certified study. Dataset: [`tests/fixtures/indiana_dor_rule_benchmark.json`](tests/fixtures/indiana_dor_rule_benchmark.json); results: [`evidence/official-source-benchmark-results.json`](evidence/official-source-benchmark-results.json).

### Current official-link check

The read-only HTTPS check on 2026-10-10 received HTTP 200 with same-host final URLs for the DOR utility page, bulletin index, Bulletins #11/#29/#55/#64, DOR forms index, direct ST-200 and ST-200R PDF downloads, and the cited Minnesota and Texas alternatives. Full response details are in [`evidence/official-source-link-check-2026-10-10.json`](evidence/official-source-link-check-2026-10-10.json). This verifies reachability and response types, not legal interpretation, rate accuracy, or tariff availability. The earlier report that direct form downloads returned 403 is superseded by this check.

### Remaining owner actions

Benjamin chooses Indiana or an alternative launch state after reviewing [DECISION.md](DECISION.md), supplies local case records and any required study, and personally reviews, signs, and submits any application. Before charging customers, he must obtain any needed legal opinion and approve the fee model, price, and legal basis. Billing remains disabled. These are the venture's remaining owner gates; no application is a tax determination or DOR approval.

## PH12.18 drift check

1. **Checkpoint:** PH12.18, Venture: Utility audits.
2. **Dependencies:** PH12 exit is not complete. ORCHESTRATION wave 6 explicitly allows assigned venture cards to start; this card does not change checkpoint status.
3. **Property and metric:** P-CONTROL (signature, payment, account, utility contact, and filing stay human actions), P-USABLE; M-VERIFIED and M-TTFA.
4. **Existing tool:** no existing utility exemption estimator or study-CSV intake flow was found. This uses local Python and the existing Glacier approval/command/check flow nodes; it does not add a paid service or shared platform block.
5. **Acceptance test, written first:** `~/w/glacier-lean/.venv/bin/python -m pytest ventures/utility-audits/tests/acceptance/test_v_utility2.py::test_utility_bills_csv_builds_unsigned_st200_application_data -q --runxfail`; it requires a callable CSV-to-ST-200 preparer and an unsigned/unsubmitted result. The existing fixture check expects a 64% meter-use screen, annual future exemption estimate, and unsigned/unsubmitted application data; a nonconsecutive study period must return uncertainty. The full venture command is `~/w/glacier-lean/.venv/bin/python -m pytest ventures/utility-audits -q`.

## Rule and source verification

Indiana DOR's current bulletin index lists #55, “Application of Sales Tax to Sales of Utilities Used in Manufacturing, Production, Recycling, Floriculture, and Arboriculture,” with July 2022 effective date. It remains the directly applicable bulletin for utility-use studies: the DOR bulletin says each meter is considered separately and the 100% meter exemption requires **more than 50%** exempt use; Form ST-200 is the application. DOR's utility page also points customers to gas and electric study workpapers. Bulletin #64, effective October 1, 2026, covers production exemptions and informs qualifying-use analysis; it does not replace utility-specific Bulletin #55.

Bulletin #29 remains linked only for the restaurant branch: its current Appendix B contains the annual 75% prepared-food formula. Bulletin #11 (January 2026) covers restaurants and cross-references #29 for food-sale examples. General predominant-use cases use #55 and ST-200. Launch-state tradeoffs and alternatives are in [DECISION.md](DECISION.md).

Official source URLs checked October 10, 2026:

- [Indiana DOR utility exemption page](https://www.in.gov/dor/i-am-a/business-corp/utility-sales-tax-exemption/) — reachable.
- [Indiana DOR bulletin index](https://www.in.gov/dor/resources/tax-library/information-bulletins/) — reachable; #11 Jan 2026, #29 Sep 2025, #55 effective Jul 2022, #64 effective Oct 1, 2026.
- [Bulletin #11](https://www.in.gov/dor/files/reference/sib11.pdf), [Bulletin #29](https://www.in.gov/dor/files/reference/sib29.pdf), [Bulletin #55](https://www.in.gov/dor/files/sib55.pdf), [Bulletin #64](https://www.in.gov/dor/files/reference/sib64.pdf) — reachable from official DOR pages.
- [Indiana DOR sales tax forms index](https://www.in.gov/dor/tax-forms/business/sales-tax-forms/index.html) — reachable and lists ST-200 and ST-200R.
- The direct form downloads [ST-200](https://forms.in.gov/Download.aspx?id=14085) and [ST-200R](https://forms.in.gov/Download.aspx?id=16301) returned HTTP 403 to the research fetcher; both are linked from the accessible DOR forms index. The links are retained as official downloads, with the index provided as the accessible alternative.
- Sample rate URLs under `utility.example` are fake test placeholders and are marked **unreachable / not a rate source**. No current customer utility tariffs were supplied or verified. Runtime `reachable_unverified` means only that the customer's HTTPS link answered on the same host; it does not verify official source identity, tariff terms, or plan availability.

## Fixture result

The fixture `tests/fixtures/indiana_predominant_use_bills.csv` is synthetic. Its bill columns are 12 months of 1,000 usage units, $70 reported tax per month, and an `exempt_use_units` allocation supplied as study evidence (640 per month). Bills themselves do not identify exempt use. The calculator screens 64% exempt use and $840 estimated annual tax exemption **only after DOR approval**, for one meter. It emits missing official customer fields and `signed: false`, `submitted: false`. It does not certify the usage study or calculate the partial production/refund path below 50%.

## Commands and results

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/utility-audits/tests/acceptance/test_v_utility2.py::test_utility_bills_csv_builds_unsigned_st200_application_data -q --runxfail` — **1 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/utility-audits/tests/acceptance -q --runxfail` — **3 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/utility-audits -q` — **13 passed, 2 xpassed** (the independent acceptance checks previously marked xfail now pass).
- `prepare_st200` smoke check using the synthetic CSV — **64%**, `$840.00`, SHA-256 provenance present, local JSON draft written, `signed: false`, `submitted: false`.
- `~/w/glacier-lean/.venv/bin/python ventures/utility-audits/scripts/utility_audit.py study --input ventures/utility-audits/tests/fixtures/indiana_predominant_use_bills.csv --output /tmp/utility-audit-st200-study.json` — **64%**, `$840.00`, ST-200 application data present, `signed: false`, `submitted: false`.
- `~/w/glacier-lean/.venv/bin/python -m ventures.install_all --only utility-audits --dry-run` — both `utility-audit-calculator` and `utility-predominant-use` validated.
- Per-venture tests were run with each venture root on `PYTHONPATH`: every suite passed except the existing recall-checker vocabulary assertion (10 passed, 1 failed; expected `no match`, got `no match found`). Recall Actor had one skip. A top-level `pytest ventures -q` invocation also cannot collect hyphenated venture packages/import roots; running the suites individually with their package roots collected them correctly. The recall-checker discrepancy is already recorded in `ventures/OWNER-START-HERE.md` and its existing claim; it is outside this card.
- `cd glacier/web && npm run live` — the real FastAPI backend started and `/api/health` returned **200 OK**, then the dev screen failed to start because `glacier/web/node_modules/vite/bin/vite.js` is missing. No full live flow walkthrough occurred. The earlier shared heavy-job wait is recorded in `vault/claims/2026-10-10-v-utility-live-lock.md`; this worktree's missing Vite dependency is a separate environment issue outside this card's file list. The CSV result remains fixture-tested, not live-tested.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests/acceptance -q --runxfail` — **2 passed, 2 failed** in unrelated `V-OWNERGUIDE` checks (venture-manifest coverage and required live-account facts). This builder card is limited to `ventures/utility-audits`; the owner guide and its acceptance checks were not changed.

No restaurant bills, certified utility study, live customer tariff, utility account, tax account, signature, payment, external message, or filing was used. Billing remains disabled pending owner approval of its model and legal basis.
