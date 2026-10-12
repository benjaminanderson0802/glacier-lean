# Public reader sample labels: provenance

## Scope and method

I transcribed these labels independently from the seven local public-source PDFs listed in `manifest.json`, using the document-reader requirements in the Venture Build Spec. The PDFs already present in `samples/documents/` were treated as the source of truth. I used page text extraction to locate candidate fields and visually inspected the relevant rendered pages where the PDF stores a figure as an image. Page numbers below are the PDF page numbers (and match the printed page numbers where shown).

I did not use reader output to choose values. A value is labeled blank only when the source form shows the target field with no entered value. I marked a field uncertain when the source contains multiple plausible values and the schema gives no way to select one. Blank values are represented as the empty string with `blank: true`; the uncertain CPSC scalar is represented by `null` with `uncertain: true` and a reason. These are source observations, not values inferred from general guidance.

## Field labels

| Document | Field | Frozen label | Source provenance |
| --- | --- | --- | --- |
| `cpsc-quick-start-guide.pdf` | `certifier_id` | `ABCCo` | PDF p. 9, Certificate Identifier example: certifier ID for importer ABC Co. |
| `cpsc-quick-start-guide.pdf` | `product_id` | `A1234567` | PDF p. 9, Product ID example for ABC Co.'s product SKU. |
| `cpsc-quick-start-guide.pdf` | `version_id` | `V1` | PDF p. 9, Version ID example for the first certificate version. |
| `cpsc-product-registry-guide.pdf` | `primary_product_id` | **uncertain** | PDF p. 45, Figure 8 has three populated product rows and three Primary Product ID values: `1422-78921-9896`, `5 34976 81564 8`, and `1234-56789-0123`. The schema names the column but does not identify a row; selecting one as the scalar answer would be arbitrary. |
| `fda-cosmetic-labeling-guide.pdf` | `example_ingredient` | `castor oil` | PDF p. 21, hypothetical lipstick's Correct Label Copy column lists “Castor Oil.” The nearby Incorrect Label Copy says “Caster Oil”; the labeled value follows the explicitly marked correct example. |
| `fda-form-5067.pdf` | `responsible_person_name` | **blank** (`""`) | PDF p. 1, Section II, “RESPONSIBLE PERSON NAME*” field is unfilled. |
| `fda-form-5067.pdf` | `product_name` | **blank** (`""`) | PDF p. 1, Section II, “PRODUCT NAME*” rows are unfilled. |
| `sample-bill-of-lading.pdf` | `bill_of_lading_number` | **blank** (`""`) | PDF p. 1, the B/L NUMBER box on the unfilled Standard Form 1103 is empty. |
| `sample-bill-of-lading.pdf` | `shipper_name` | **blank** (`""`) | PDF p. 1, “SHIPPER NAME AND ADDRESS” box on the unfilled Standard Form 1103 is empty. |
| `sample-energy-bill.pdf` | `monthly_usage` | `557` | PDF p. 1, sample bill usage line for the current service period shows 557 kWh. PDF p. 2 repeats 557 kWh for the same service period; p. 1 is the cited label page. |
| `sample-property-tax-bill.pdf` | `parcel_number` | `12-116-0029-0000` | PDF p. 1, `PARCEL#` field. |
| `sample-property-tax-bill.pdf` | `owner_name` | `BILL AND SUE HOMEOWNER` | PDF p. 1, named property owner/address block. |
| `sample-property-tax-bill.pdf` | `assessed_value` | `98,900` | PDF p. 1, `Total Assessed Value` column. |

## Uncertainty and blank-field notes

- The CPSC registry guide is instructional and its Figure 8 shows three valid example rows. No single row is privileged by the `primary_product_id` schema, so the scalar label stays uncertain rather than encoding one row as if it were uniquely correct.
- FDA Form 5067 and GSA Standard Form 1103 are blank forms for the requested fields. Their blank labels record that the public source contains no entered name or B/L number; they are not missing values to infer from surrounding agency text.
- The energy-bill usage label is the current monthly usage (557 kWh), not the separate historical series printed elsewhere on the bill.

No benchmark was run as part of labeling. The manifest is frozen against source pages before any engine-agreement result is observed.
