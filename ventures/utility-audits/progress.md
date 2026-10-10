# Utility audits progress

PH12.18 remains in progress pending owner confirmation of Indiana as the launch state. Flat-rate source links are now checked for HTTPS reachability and same-host redirects. Loopback/private literal addresses and malformed links are rejected before fetch. A reachable link is explicitly labeled `reachable_unverified`; the tool does not claim that the source is official or that the full tariff/availability is confirmed, and it lists unsupported charges. An unavailable or invalid source makes the rate result uncertain.

Owner steps link directly to Indiana DOR's utility-exemption page, Bulletins #11 and #29, and the ST-200R form. Billing is disabled until the owner records approval of the fee model and legal basis. The customer continues to sign and submit state forms.

`/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/utility-audits/tests` — 9 passed. Real restaurant bills and tariff records were not available; rate tests use mocked HTTP responses and synthetic fixture data. Real Glacier runtime and owner state confirmation remain outstanding under the existing heavy-job claim.
