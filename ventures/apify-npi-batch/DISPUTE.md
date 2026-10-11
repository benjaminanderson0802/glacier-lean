# Acceptance test dispute

`test_no_match_is_explicit_and_free` currently asserts
`'no match found in NPPES as of' in rows[0]['message'].lower()`. Lowercasing the
message converts `NPPES` to `nppes`, so the uppercase expected literal can
never match any ordinary string. The product message is
`No match found in NPPES as of <UTC date>; ...`, includes the required source
and date, and the row remains a free `no_match` result. The assertion should
use a lowercase expected literal or compare the original message
case-insensitively.

No acceptance check or product test was changed to work around this mismatch.
