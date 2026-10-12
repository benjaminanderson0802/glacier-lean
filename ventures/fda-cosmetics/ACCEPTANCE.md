# Acceptance — V-FDA2

1. Read Shopify Admin GraphQL product records using the read-only Shopify client and map product details into FDA Form 5067/Cosmetics Direct listing fields.
2. Attach a source for every prepared field; leave brand-confirmed information uncertain where Shopify data or label evidence cannot establish it.
3. Include ingredient and label review checklist items and reminders at 120 days and annually.
4. Keep FDA listing submission with the owner; no API call or browser step submits a listing.
5. Provide a read-only owner check using Glacier keychain secrets and never print secret values.
6. Keep `PROOF.md` explicit about fixture-only versus live Shopify/FDA evidence.
