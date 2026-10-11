---
id: CLM-2026-10-11-B-READER-OCR-IMAGE-ACCEPTANCE
filed_by: B-READER-OCR
run_id: null
node_id: null
checkpoint: PH12.4
kind: unclear_spec
summary: Independent frozen image acceptance input is missing for B-READER-OCR
evidence: "The card requires a frozen independent image sample, real Tesseract, and the configured local model. The available reader release evidence at evidence/backlog/B-READER-LABELS/release-benchmark.md covers seven PDF fixtures only. The card assigns evaluation data to B-READER-LABELS and prohibits this builder from labeling its own benchmark. No image sample, expected field/page labels, or independent image acceptance case was found in the reader evidence. `command -v tesseract` also reproduces the recorded missing executable in this worktree."
attempts_made: 0
status: filed
assigned_to: reader-evaluator
resolution: null
resolution_evidence: null
---

Before implementation, provide an independently frozen image fixture and its
field/page expectations (or an equivalent evaluator-owned acceptance case) for
this card. The fixture must let the builder verify real Tesseract extraction
and the configured local-model cross-check without labeling the builder's own
benchmark. Once available, the reader-runtime builder can add ordinary tests
and proceed with the isolated setup work.
