# Freight claim customer intake checklist

Use this checklist to give the shipper enough information for Glacier to prepare a claim packet. ShipStation provides shipment facts only; a CSV does not prove damage, loss, value, or coverage. Glacier does not send a claim. The shipper checks and files the packet with the carrier.

## Shipment and issue

- [ ] ShipStation shipment/order number, carrier, service, tracking number (or LTL PRO number), ship date, and delivery or expected-delivery date.
- [ ] Choose the issue: damage, missing contents, shortage, or not delivered. Describe what happened and when it was discovered. Enter `shipment_type` as `damage` for damage/shortage/missing contents or `lost` for a shipment not delivered; leave it unknown rather than guessing.
- [ ] Confirm the shipment origin/destination and whether it was domestic or international.
- [ ] For LTL, provide the signed bill of lading, NMFC item number, freight class, commodity description, pallet/package count, and weight shown at tender.

## What to attach

- [ ] Bill of lading / shipping receipt and carrier label or tracking record.
- [ ] Delivery receipt / proof of delivery, including handwritten exception or shortage notes.
- [ ] Commercial invoice showing the affected items, quantity, and unit value. Mark exactly which items and quantities were lost or damaged; confirm the arithmetic.
- [ ] Dated photos of the affected goods, packaging, pallet, and labels. Keep the original item and packaging until the carrier says they can be discarded or the claim is resolved.
- [ ] Repair estimate, statement that repair is not possible, or salvage value when applicable.
- [ ] Insurance / declared-value / coverage record, freight bill and proof of freight charges when available, inspection report, and carrier correspondence.
- [ ] Any carrier-specific evidence listed in the packet. A carrier may request more evidence or an inspection.

## Confirm before a packet can be prepared

- [ ] Confirm the carrier's exact service and current filing deadline from its current official page and the shipment terms. The dates Glacier calculates are reminders to verify, not a promise that a filing is timely.
- [ ] Confirm that the terms URL, effective date, declared value / liability limit, insurance, and requested claim amount apply to this shipment.
- [ ] Confirm which person or business owns the claim and may file it.
- [ ] Provide the carrier claim recipient or portal to the shipper. Never put a carrier login or secret in an intake file.

## Carrier timing guide

- [UPS](https://www.ups.com/us/en/support/file-a-claim): start a lost or damaged package claim within 60 days after scheduled delivery. Damage photos and keeping the goods/packaging may be needed; see [UPS supporting documents](https://www.ups.com/us/en/support/file-a-claim/supporting-documents).
- [FedEx](https://www.fedex.com/en-us/customer-support/claims.html): damage/missing contents are due within 60 calendar days of shipment for U.S. packages or 21 days for international packages; lost shipments within nine months. Confirm the service and current instructions.
- [USPS](https://faq.usps.com/articles/Knowledge/Domestic-Claims-The-Basics): damage/missing contents are due within 60 days after mailing. Lost-mail deadlines vary by service; check the current [Domestic Mail Manual 609](https://pe.usps.com/TEXT/DMM300/609.htm). Insurance proof, value proof, damage evidence, and retention of the package/item may be required.
- LTL: if the Carmack Amendment applies, 49 U.S.C. § 14706 sets a minimum nine-month filing period. The bill of lading and tariff can control the exact date. A written claim must identify the shipment, assert liability, and state a specified or determinable amount; a delivery-receipt notation alone is not a claim. See [49 U.S.C. § 14706](https://uscode.house.gov/view.xhtml?edition=prelim&num=0&req=granuleid%3AUSC-prelim-title49-section14706) and [49 CFR § 370.3](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-370/section-370.3).

For LTL claims governed by 49 CFR Part 370, record the carrier receipt date and reference. The response tracker reminds the shipper to look for acknowledgment/disposition by day 30 and disposition or a status notice by day 120; if still pending, the regulation calls for status updates every 60 days. UPS, FedEx, and USPS response timing is not represented here as a guaranteed date: record the carrier's receipt, reference, and any date it promises, then follow up with the carrier.

## After the shipper files

- [ ] The shipper reviews the final packet. The shipper submits it through its chosen carrier channel.
- [ ] Save the carrier's receipt/confirmation, reference number, and actual received date in `incoming/receipt.json` so Glacier can start response-date reminders.
- [ ] Record each carrier update and any promised response date. The customer decides whether to accept or decline a full-release settlement.

This checklist is operational help, not legal advice. Carrier rules, contracts, service type, and shipment facts can change the applicable deadline and evidence requirements. Verify them before filing.
