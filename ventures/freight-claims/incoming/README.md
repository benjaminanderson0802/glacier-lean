# Freight claim intake

Place the customer-confirmed intake record at `$GLACIER_HOME/ventures/freight-claims/incoming/claim-intake.json`. Put its supporting files in `$GLACIER_HOME/ventures/freight-claims/incoming/customer-uploads/` and reference each absolute file path in the record. The venture currently uses a local on-device handoff; it does not expose a hosted upload link.

Required document keys are `delivery_receipt`, `photos`, `commercial_invoice`, and `bill_of_lading`. Each may be one file path or a list of paths. Do not include credentials in the intake file.
