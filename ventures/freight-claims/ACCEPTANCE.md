# Acceptance — V-FREIGHT2

1. Parse ShipStation shipment CSV exports into normalized shipment records and retain shipment, order, carrier, tracking, ship date, and item references.
2. Prepare source-linked packet templates for UPS, FedEx, USPS, and LTL/Carmack with required evidence and carrier-specific claim deadlines.
3. Track carrier response dates and expose a customer-facing intake checklist for invoices, delivery receipts, photographs, and related evidence.
4. Convert ShipStation CSV fixture input into draft claim packets without contacting carriers or submitting claims.
5. Keep authorization, sending, settlement decisions, invoices, and payment actions behind owner/customer review and approval.
6. Keep `PROOF.md` explicit about fixture-only versus live ShipStation/carrier activity.
