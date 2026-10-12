# Acceptance test dispute

`test_explicit_empty_result_is_free_no_match` currently asserts
`'no match found in FDIC as of' in rows[0]['message'].lower()`. Lowercasing the
message converts `FDIC` to `fdic`, so the uppercase expected literal can never
match any ordinary string. The product message is
`No match found in FDIC as of <UTC date>; ...`, includes the required source and
date, and the row remains a free `no_match` result. The assertion should use a
lowercase expected literal or compare the original message case-insensitively.

No acceptance check or product test was changed to work around this mismatch.
