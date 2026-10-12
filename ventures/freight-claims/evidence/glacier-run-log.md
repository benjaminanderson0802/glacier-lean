# Local Glacier run log (synthetic fixtures)

Captured from the real local Glacier API after each run.

## freight-watch-shipstation — 3336faf13477

Status: `done`; verified: `True`; waiting on: `None`.

Node states:
- `candidate_note`: `done`
- `daily`: `done`
- `read_shipments`: `done`

Outputs:
```json
{
  "candidate_note": "ventures/freight-claims/reports/shipstation-3336faf13477.md (commit e6d200c9)",
  "daily": "",
  "read_shipments": "{\n  \"result\": \"match\",\n  \"checked_on\": \"2026-10-10\",\n  \"candidate_count\": 1,\n  \"candidates\": [\n    {\n      \"shipment_id\": \"1042\",\n      \"signal\": \"possible damage or delivery exception\",\n      \"customer_confirmation_required\": true,\n      \"tracking_number\": \"A1B2C3D4E5\"\n    }\n  ],\n  \"source\": \"csv\",\n  \"side_effects\": [],\n  \"csv_file\": \"/tmp/gf-rg-freight-live/ventures/freight-claims/incoming/shipstation-shipments.csv\",\n  \"skipped_rows\": []\n}\n"
}
```

## freight-prepare-claim — fbaf166507d9

Status: `waiting`; verified: `None`; waiting on: `owner_input_ready`.

Node states:
- `approve_customer_submission`: `pending`
- `owner_first_ten`: `pending`
- `owner_input_ready`: `waiting`
- `packet_note`: `pending`
- `prepare_packet`: `pending`
- `record_owner_review`: `pending`
- `upload_instructions`: `done`

Outputs:
```json
{
  "upload_instructions": "ventures/freight-claims/incoming/README.md (commit 67c146ec)"
}
```

## freight-prepare-claim-fixture-e2e — bf91121187a4

Status: `done`; verified: `True`; waiting on: `None`.

Node states:
- `packet_note`: `done`
- `prepare_packet`: `done`
- `upload_instructions`: `done`

Outputs:
```json
{
  "packet_note": "ventures/freight-claims/reports/claim-packet-bf91121187a4.md (commit 66671fc0)",
  "prepare_packet": "{\n  \"result\": \"match\",\n  \"source\": \"csv\",\n  \"csv_file\": \"/tmp/gf-rg-freight-live/ventures/freight-claims/incoming/shipstation-shipments.csv\",\n  \"candidate_count\": 1,\n  \"packet_count\": 1,\n  \"packets\": [\n    {\n      \"venture\": \"freight-claims\",\n      \"shipment_id\": \"SS-ORD-1042\",\n      \"carrier\": \"UPS\",\n      \"tracking_number\": \"A1B2C3D4E5\",\n      \"result\": \"match\",\n      \"claimed_value\": \"250.00\",\n      \"damaged_items\": [\n        {\n          \"description\": \"Synthetic ceramic tile\",\n          \"quantity\": 1,\n          \"invoice_unit_price\": \"250.00\",\n          \"claimed_value\": \"250.00\",\n          \"customer_confirmed\": true\n        }\n      ],\n      \"liability_limit_estimate\": \"250.00\",\n      \"carrier_terms\": {\n        \"source_url\": \"https://www.ups.com/us/en/support/file-a-claim\",\n        \"effective_date\": \"2026-10-10\",\n        \"customer_confirmed\": true\n      },\n      \"documents\": {\n        \"delivery_receipt\": [\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/delivery-receipt.txt\"\n        ],\n        \"photos\": [\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/damage-photo-note.txt\"\n        ],\n        \"commercial_invoice\": [\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/commercial-invoice.txt\"\n        ],\n        \"bill_of_lading\": [\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/blocks/reader/samples/documents/sample-bill-of-lading.pdf\"\n        ]\n      },\n      \"missing_documents\": [],\n      \"damaged_item_values_confirmed_by_customer\": true,\n      \"insurance_instruction\": \"customer reports no separate shipment insurance\",\n      \"document_reads\": [\n        {\n          \"kind\": \"delivery_receipt\",\n          \"path\": \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/delivery-receipt.txt\",\n          \"fields\": {\n            \"shipment_id\": {\n              \"value\": \"ss-demo-001\",\n              \"page\": 1,\n              \"confidence\": 0.65,\n              \"uncertain\": false\n            },\n            \"invoice_number\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_total\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            }\n          },\n          \"text_excerpt\": \"Shipment ID: ss-demo-001\\nException: one pallet damaged at delivery\\nDate: 2026-09-01\\n\",\n          \"read_error\": null\n        },\n        {\n          \"kind\": \"photos\",\n          \"path\": \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/damage-photo-note.txt\",\n          \"fields\": {\n            \"shipment_id\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_number\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_total\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            }\n          },\n          \"text_excerpt\": \"Synthetic photo evidence placeholder for local Glacier dry run; no customer image data.\\n\",\n          \"read_error\": null\n        },\n        {\n          \"kind\": \"commercial_invoice\",\n          \"path\": \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/commercial-invoice.txt\",\n          \"fields\": {\n            \"shipment_id\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_number\": {\n              \"value\": \"INV-DEMO-001\",\n              \"page\": 1,\n              \"confidence\": 0.65,\n              \"uncertain\": false\n            },\n            \"invoice_total\": {\n              \"value\": \"330.00\",\n              \"page\": 1,\n              \"confidence\": 0.65,\n              \"uncertain\": false\n            }\n          },\n          \"text_excerpt\": \"Invoice Number: INV-DEMO-001\\nInvoice Total: 330.00\\nDamaged widget A quantity 2 unit price 125.00\\n\",\n          \"read_error\": null\n        },\n        {\n          \"kind\": \"bill_of_lading\",\n          \"path\": \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/blocks/reader/samples/documents/sample-bill-of-lading.pdf\",\n          \"fields\": {\n            \"shipment_id\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_number\": {\n              \"value\": null,\n              \"page\": null,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            },\n            \"invoice_total\": {\n              \"value\": null,\n              \"page\": 1,\n              \"confidence\": 0.0,\n              \"uncertain\": true\n            }\n          },\n          \"text_excerpt\": \"B/L NUMBER\\nU.S. GOVERNMENT BILL OF LADING\\nINTERNATIONAL AND DOMESTIC OVERSEAS SHIPMENTS\\nTRANSPORTATION COMPANY TENDERED TO SCAC DATE B/L PREPARED\\nDESTINATION NAME AND ADDRESS SPLC (Dest.) ORIGIN NAME AND ADDRESS\\nSPLC (Orig.)\\nCONSIGNEE (Name and full address of installation) GBLOC (Cons.) SHIPPER NAME AND ADDRESS\\nAPPROPRIATION CHARGEABLE BILL CHARGES TO (Dept./agency, bureau/office mailing AGENCY LOC CODE\\naddress and ZIP code)\\nVIA (Route shipment when advantageous to the Government)\\nMARKS AND ANNOTATIONS\\nPACKAGES DESCRIPTION OF ARTICLES (Use carrier's classification or tariff description 19. WE\",\n          \"read_error\": null\n        }\n      ],\n      \"customer_email_draft\": {\n        \"to\": \"claims@example.test\",\n        \"subject\": \"Freight claim — A1B2C3D4E5\",\n        \"body\": \"Please review this freight claim for shipment SS-ORD-1042 (A1B2C3D4E5).\\n\\nDamaged invoice items only:\\n- 1 × Synthetic ceramic tile: $250.00\\n\\nClaimed invoice value: $250.00\\nEstimated liability limit: $250.00 based on https://www.ups.com/us/en/support/file-a-claim (effective 2026-10-10).\\nThe shipper has reviewed the attached documents and claim details. Please acknowledge receipt and provide a claim reference.\\nThis draft has not been sent; the customer must review it and submit it through their chosen carrier channel.\",\n        \"attachments\": [\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/delivery-receipt.txt\",\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/damage-photo-note.txt\",\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/commercial-invoice.txt\",\n          \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/blocks/reader/samples/documents/sample-bill-of-lading.pdf\"\n        ],\n        \"sent\": false\n      },\n      \"side_effects\": [],\n      \"human_review_required\": true,\n      \"carrier_claim_guidance\": {\n        \"carrier\": \"UPS\",\n        \"filing_deadline_days\": 60,\n        \"filing_deadline_months\": null,\n        \"filing_deadline_anchor\": \"scheduled_delivery_date\",\n        \"deadline_note\": \"Start a lost or damaged package claim within 60 days of scheduled delivery; confirm the exact service and shipment terms.\",\n        \"deadline_requires_service_lookup\": false,\n        \"required_evidence\": [\n          \"tracking number or carrier PRO/reference\",\n          \"bill of lading or shipping receipt\",\n          \"itemized commercial invoice or other proof of value\",\n          \"delivery receipt / proof of delivery, including any exception notation\",\n          \"claim amount tied to customer-confirmed damaged, lost, or short items\",\n          \"invoice or other merchandise-value support\",\n          \"three damage photos: item as packed, close-up shipping label, and outside package damage\",\n          \"package dimensions for damage claims; retain contents and packaging for possible inspection\"\n        ],\n        \"sources\": [\n          {\n            \"title\": \"UPS File a Claim\",\n            \"url\": \"https://www.ups.com/us/en/support/file-a-claim\"\n          },\n          {\n            \"title\": \"UPS Supporting Documents for Claims\",\n            \"url\": \"https://www.ups.com/us/en/support/file-a-claim/supporting-documents\"\n          }\n        ],\n        \"template_id\": \"ups\",\n        \"filing_deadline\": \"2026-12-08\",\n        \"deadline_anchor_date\": \"2026-10-09\",\n        \"filing_deadline_status\": \"estimated — customer must confirm carrier service and terms\",\n        \"evidence_checklist\": [\n          {\n            \"item\": \"tracking number or carrier PRO/reference\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"bill of lading or shipping receipt\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"itemized commercial invoice or other proof of value\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"delivery receipt / proof of delivery, including any exception notation\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"claim amount tied to customer-confirmed damaged, lost, or short items\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"invoice or other merchandise-value support\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"three damage photos: item as packed, close-up shipping label, and outside package damage\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          },\n          {\n            \"item\": \"package dimensions for damage claims; retain contents and packaging for possible inspection\",\n            \"provided\": false,\n            \"customer_confirmed\": false\n          }\n        ]\n      },\n      \"response_tracking\": {\n        \"carrier_filed_date\": null,\n        \"carrier_received_date\": null,\n        \"carrier_reference\": null,\n        \"carrier_response_due_on\": null,\n        \"milestones\": [],\n        \"note\": \"Record the carrier's receipt, reference, and any promised response date after the shipper files. Parcel-carrier response timing is not a published commitment in these sources.\"\n      },\n      \"packet_path\": \"/tmp/gf-rg-freight-live/ventures/freight-claims/packets/claim-c2f741b863f7cfbe9427.json\"\n    }\n  ],\n  \"needs_customer_intake\": [],\n  \"skipped_rows\": [],\n  \"side_effects\": []\n}\n",
  "upload_instructions": "ventures/freight-claims/incoming/README.md (commit d93a2fbb)"
}
```

## freight-record-carrier-receipt — 75f3f083fa79

Status: `done`; verified: `True`; waiting on: `None`.

Node states:
- `receipt_note`: `done`
- `record_receipt`: `done`

Outputs:
```json
{
  "receipt_note": "ventures/freight-claims/reports/carrier-receipt-75f3f083fa79.md (commit 8f8c6b4c)",
  "record_receipt": "{\n  \"claim_id\": \"fixture-ship-9001\",\n  \"carrier\": \"UPS\",\n  \"carrier_received_date\": \"2026-09-10\",\n  \"carrier_reference\": \"FIXTURE-RECEIPT-9001\",\n  \"carrier_response_due_on\": null,\n  \"confirmation_document\": \"/home/glacier/w/workers/gf-RG-FREIGHT/ventures/freight-claims/tests/fixtures/delivery-receipt.txt\",\n  \"deadline_rule\": \"30d|120d\",\n  \"response_tracking\": {\n    \"milestones\": [],\n    \"carrier_response_due_on\": null,\n    \"note\": \"For parcel carriers, this is a customer-entered follow-up date, not a published response promise.\"\n  },\n  \"result\": \"match\",\n  \"side_effects\": [],\n  \"record_path\": \"/tmp/gf-rg-freight-live/ventures/freight-claims/reports/receipt-29e4b2464884ab9dad5b.json\"\n}\n"
}
```

## freight-check-deadlines — 75fe4386da35

Status: `done`; verified: `True`; waiting on: `None`.

Node states:
- `daily`: `done`
- `deadline_note`: `done`
- `due_items`: `done`

Outputs:
```json
{
  "daily": "",
  "deadline_note": "ventures/freight-claims/reports/deadlines-75fe4386da35.md (commit b87bbd4e)",
  "due_items": "{\n  \"result\": \"match\",\n  \"checked_on\": \"2026-10-10\",\n  \"reminders\": [\n    {\n      \"item_id\": \"fixture-ship-9001\",\n      \"label\": \"Freight claim fixture-ship-9001: check carrier status\",\n      \"rule\": \"30d|120d\",\n      \"date\": \"2026-10-10\",\n      \"milestone\": \"reminder\",\n      \"glacier_steps\": [\n        {\n          \"type\": \"note\",\n          \"config\": {\n            \"path\": \"ventures/deadline-reminders/29e4b2464884ab9d-2026-10-10.md\",\n            \"template\": \"# Freight claim fixture-ship-9001: check carrier status\\n\\nReminder on 2026-10-10.\\n\\n{summary}\"\n          }\n        },\n        {\n          \"type\": \"approval\",\n          \"config\": {\n            \"prompt\": \"Review deadline: Freight claim fixture-ship-9001: check carrier status is reminder on 2026-10-10. Mark this reminder acknowledged?\"\n          }\n        }\n      ]\n    }\n  ],\n  \"side_effects\": []\n}\n"
}
```
