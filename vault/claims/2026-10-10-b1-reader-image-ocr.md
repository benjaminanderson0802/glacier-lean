---
id: CLM-2026-10-10-B1-READER-IMAGE-OCR
filed_by: B1
run_id: null
node_id: null
checkpoint: PH12.4
kind: capability_gap
summary: Photo OCR cannot run because the worker image has no Tesseract executable
evidence: "In /home/glacier/w/workers/gf-B1, `command -v tesseract` returned no path. Pillow 12.3.0 is installed, but it does not recognize text. `ollama list` showed granite3.3:2b and other text-only models; the configured Granite model can cross-check extracted PDF text but cannot read image pixels."
attempts_made: 1
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The reader can extract text PDFs and CSV locally, and it uses Tesseract for raster
photos when that executable is installed. This worker image has no OCR executable,
so photo fields cannot be extracted here and the block cannot prove the photo path
from this sandbox. Tesseract is the free/open-source option named in the card; no
alternative OCR package is installed. Install Tesseract in an isolated, approved
environment, then add a public photo sample and verify that OCR text is
cross-checked by the local model. No image-only values should be accepted while
the second engine is unavailable.
