# Acceptance — V-WARRANTY2

1. Parse the documented Jobber GraphQL 2026-04-16 jobs response, including custom brand, model, serial, and install-date fields, from a fixture matching the API envelope.
2. Build a registration queue and homeowner email draft only from completed jobs with valid unit and homeowner details; preserve links back to source jobs.
3. Keep brand serial patterns unverified unless source-backed; such records say `uncertain — please check` and remain held for review.
4. Keep Jobber access read-only: never update jobs, register a product, or send homeowner email automatically.
5. Provide a one-command read-only owner check that retrieves runtime secrets from Glacier keychain and never prints or writes secret values.
6. Keep `PROOF.md` truthful about fixture versus connected-account evidence; do not claim a live Jobber run without one.
