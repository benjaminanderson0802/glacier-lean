# Freight claims

Freight claims prepares source-linked packets for possible lost, damaged, or short pallet shipments. It reads ShipStation shipment records, flags possible exceptions for the shipper to confirm, reads the bill of lading, invoice, delivery receipt, and photos with Glacier's shared document reader, and keeps carrier response deadlines on a local timeline.

The packet claims only the invoice value of items the shipper marks as damaged and confirms against the invoice. A separate liability estimate is shown only when the shipper confirms the carrier-terms URL, effective date, shipment weight, and per-pound limit. Those figures are preparation aids; the customer reviews them and decides what to claim. Missing documents, uncertain reader fields, unclear insurance coverage, and conflicting evidence stay visible.

Glacier prepares an email draft and attachment list but does not contact a carrier, submit a claim, sign for a shipper, invoice a customer, or charge a payment method. A signature request uses only an authorization document supplied and approved by the owner; the shipper signs through the shared customer block. A shipper reviews and sends its claim. The customer then provides the carrier receipt confirmation; only then does the deadline tracker start the 30- and 120-day reminders. After recovery, the invoice draft calculates the agreed 20–30% share and waits for owner review.

ShipStation access is read-only and starts disabled. Its daily run makes no API request until the owner adds `shipstation_api_key` in Glacier Settings > Secrets and creates `$GLACIER_HOME/ventures/freight-claims/shipstation-enabled.json` with `{"approved": true}` after checking the account's current plan and API-call limits. It reads shipment pages through the shared connector and, for rows with a `label_id`, calls ShipStation's documented label tracking GET. Tracking calls can exceed a plan's included monthly quota, so the owner explicitly enables polling; each run is capped at 100 tracking lookups and untrackable rows stay uncertain. See [ShipStation tracking documentation](https://docs.shipstation.com/tracking). No credential, portal account, paid service, or live transaction is created by this venture. The shared customer block's Stripe support remains test-mode only.

## Your steps

1. Connect ShipStation with a read-only key and review the first app listing.
2. Review the first ten packets against their source documents, carrier terms, and insurance status.
3. Have the shipper provide or sign owner-approved authorization, confirm the claim details, send the draft, and report the carrier receipt date and any recovery. Approve any invoice draft before it is sent.

## Run locally

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.install_all --dry-run --only freight-claims
~/w/glacier-lean/.venv/bin/python ventures/freight-claims/scripts/claims.py watch
~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests
```

Place customer-confirmed claim data and local attachment paths in `$GLACIER_HOME/ventures/freight-claims/incoming/claim-intake.json`. Use a list of records or one record with `shipment`, `damaged_items`, `documents`, `carrier_terms`, and `separate_insurance`. Set `customer_confirmed: true` on each damaged item only after the shipper checks its quantity and price against the commercial invoice. Set `carrier_terms.customer_confirmed: true` only after the shipper confirms the published terms URL, effective date, and liability limit. For a covered shipment, set `customer_requests_claim` only after the shipper explicitly asks for a carrier claim. Do not put carrier credentials in intake JSON. For an authorization request, use an owner-approved document at `incoming/owner-approved-authorization.pdf` and signer details at `incoming/signer.json`; the generated local link is not shared off-device automatically. After the shipper submits, place `claim_id`, `carrier_received_date`, `reference`, and `confirmation_document` in `incoming/receipt.json` and run the carrier receipt flow.
