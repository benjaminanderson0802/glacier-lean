# Utility audits proof

## PH12.18 drift check

1. **Checkpoint:** PH12.18, Venture: Utility audits.
2. **Dependencies:** PH12 parent exit is not yet complete. ORCHESTRATION wave 6 explicitly allows assigned venture cards to start; no checkpoint status is changed in this card.
3. **Property and metric:** P-CONTROL (customer signs/submits; no portal actions or external writes) and P-USABLE; M-VERIFIED and M-TTFA.
4. **Existing tool:** no existing utility audit calculator was found. Reuse-only shared blocks that would apply (reader/rules) are absent from this base branch. UtilityAPI/Arcadia are paid services; this build accepts customer-entered bill and tariff data and does not connect to them. No shared block is modified.
5. **Acceptance test, written first:** `/home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s ventures/utility-audits/tests -v`; covers statewide threshold inputs, the electricity estimate, missing-evidence uncertainty, period validation, and unsigned/unsubmitted output.

## Launch-state decision for owner confirmation

Recommended state: **Indiana**, limited to the restaurant electricity exemption for a seller whose annual statewide prepared-food sales percentage meets the DOR's 75% test and whose selected electricity is through one meter. Indiana DOR describes a 50% exemption of tax on single-meter electricity transactions and requires ST-200R before issuing ST-109R. Bulletin #29 says the 75% calculation is annual across all of a seller's Indiana establishments. The owner must confirm Indiana as the launch state before customer launch or any filing support is offered.

Primary references:

- Indiana DOR, [Utility Sales Tax Exemption](https://www.in.gov/dor/i-am-a/business-corp/utility-sales-tax-exemption/)
- Indiana DOR, [Sales Tax Information Bulletin #11 (January 2026)](https://www.in.gov/dor/files/reference/sib11.pdf)
- Indiana DOR, [Sales Tax Information Bulletin #29, Appendix B](https://www.in.gov/dor/reference/files/sib29.pdf)

## Commands and results

- `PYTHONDONTWRITEBYTECODE=1 /home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s ventures/utility-audits/tests -v` — **7 tests passed**, including statewide threshold, period validation, and flat-rate scenario cases.
- `/home/glacier/w/glacier-lean/.venv/bin/python -m ventures.install_all --only utility-audits --dry-run` — **utility-audit-calculator validated**.
- CLI dry-run with the synthetic 12-month sample — **result `match`, estimated annual future savings `$240.00`, ST-200R draft present, `signed: false`, `submitted: false`**. Output was written under a disposable `/tmp/utility-audit-check` home.
- Real Glacier live runtime run — not completed: `heavy npm run live` waited 15m09s for a shared heavy-job slot and was canceled per the project backstop. The environment claim is `vault/claims/2026-10-10-v-utility-live-lock.md`. The venture flow pauses at the owner-only launch-state approval; it will not proceed until the owner confirms Indiana.

Independent review found two issues and guided fixes: the 75% test is annual across all the seller's Indiana establishments, and monthly periods must be valid and consecutive. The calculator now requires customer-confirmed statewide totals, validates real and consecutive periods, and compares customer-supplied flat-rate scenarios without claiming that a cheaper plan is available. A second independent review confirmed the rate math and safety wording, and the requested manifest and flow-prompt consistency fixes are applied.

No real restaurant utility bills or rate tariffs were available for the synthetic sample. The optional rate check requires a customer to enter published flat-rate data and links; the tool does not fetch or validate them, verify availability, or model demand charges, taxes, riders, and other tariff charges. Tests use clearly synthetic customer records. No utility account, tax portal, paid API, signature, external message or filing was used.
