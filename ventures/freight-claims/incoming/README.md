# Freight claim intake

ShipStation API alternative: place a Shipments or Orders export (`.csv`) directly in this folder. The daily shipment check uses the newest CSV if API access is not enabled or the API read fails. To select a file directly, run `python ventures/freight-claims/scripts/claims.py watch --csv /path/to/export.csv`. The report lists skipped row numbers and reasons. Keep only customer shipment data needed for local claim preparation here; never include API keys.

Place the customer-confirmed intake record at `$GLACIER_HOME/ventures/freight-claims/incoming/claim-intake.json`. Put its supporting files in `$GLACIER_HOME/ventures/freight-claims/incoming/customer-uploads/` and reference each absolute file path in the record. The venture currently uses a local on-device handoff; it does not expose a hosted upload link.

Required document keys are `delivery_receipt`, `photos`, `commercial_invoice`, and `bill_of_lading`. Each may be one file path or a list of paths. Do not include credentials in the intake file.
