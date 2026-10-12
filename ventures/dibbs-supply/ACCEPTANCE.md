# Acceptance — V-DIBBS2

1. Read SAM.gov Opportunities API v2 response records from the documented `opportunitiesData` envelope and filter to DLA and the approved NAICS codes.
2. Rank eligible opportunities and prepare quote sheets only from owner-entered supplier quotes; include the exact official solicitation link and deadline.
3. Preserve the owner-provided API key as a Glacier secret; never put it in flow inputs, output, logs, fixtures, or `PROOF.md`.
4. Do not click through DIBBS consent banners or treat blocked/empty DoD pages as an empty solicitation market.
5. Keep supplier spending, bid signature, and bid submission as owner actions; tests must show no external write.
6. Distinguish SAM.gov fixture verification from a live API-key canary in `PROOF.md`.
