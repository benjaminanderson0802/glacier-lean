# Public labeled sample set

These public examples are kept for repeatable extraction checks. They contain
government guidance/forms and designated sample bills; no customer uploads or
private documents are used. Labels were transcribed from the cited source pages
and are recorded in `manifest.json`.

| File | Public source | Type |
| --- | --- | --- |
| `documents/cpsc-quick-start-guide.pdf` | [CPSC eFiling Quick Start Guide](https://www.cpsc.gov/s3fs-public/eFiling_Quick_Start_Guide_V1-1.pdf) | Certificate of compliance example data |
| `documents/cpsc-product-registry-guide.pdf` | [CPSC Product Registry User Guide](https://www.cpsc.gov/s3fs-public/eFiling_Product_Registry_User_Guide_V3.pdf) | Certificate data and registry examples |
| `documents/fda-cosmetic-labeling-guide.pdf` | [FDA Cosmetic Labeling Guide](https://www.fda.gov/media/88234/download) | FDA cosmetic label examples |
| `documents/fda-form-5067.pdf` | [FDA Form 5067](https://www.fda.gov/media/175263/download) | Cosmetic listing form (blank fields are labeled blank) |
| `documents/sample-bill-of-lading.pdf` | [GSA Standard Form 1103](https://www.gsa.gov/system/files/SF_1103.pdf) | Public bill of lading form |
| `documents/sample-energy-bill.pdf` | [EPA sample energy bill](https://www.epa.gov/sites/default/files/2015-05/documents/sample-elec-bill.pdf) | Public electricity bill example |
| `documents/sample-property-tax-bill.pdf` | [Wisconsin sample property tax bill](https://www.revenue.wi.gov/documents/property-tax-bill-sample.pdf) | Public property tax example |

The two CPSC publications, FDA publications, GSA form, EPA bill, and Wisconsin
tax bill are government-published public examples. Their SHA-256 digests and
manually labeled values are in the manifest. Only nonblank fields with an
explicit value in the public source are scored for extraction agreement; blank
sample forms remain in the set as format examples, not as successful extracts.
Review the labels against their cited pages before extending the benchmark;
agreement must not be obtained by changing labels to match an engine's output.
