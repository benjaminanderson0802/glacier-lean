# Disputed legacy check

## `AlabamaRosterTests.test_exact_business_name_match_only_and_no_match_is_dated`

This existing unit check expects the no-match outcome to say `2026-10-10`, the
lookup date, although the supplied roster's `roster_as_of` value is
`2026-10-01`. That conflicts with the independent acceptance contract in
`ACCEPTANCE.md`: no-match must refer to the dated roster snapshot, because the
result says nothing about records added after that snapshot.

Corrected assertion: expect `no match found in supplied Alabama roster as of
2026-10-01`. The implementation follows the roster snapshot date. This check
was left unchanged under invariant I-04.
