---
id: CLM-2026-10-10-B-READER-LABELS-AGREEMENT
filed_by: B-READER-LABELS
run_id: null
node_id: null
checkpoint: PH12.4
kind: bug
summary: Frozen public reader labels measure below the 95% release agreement criterion
evidence: "evidence/backlog/B-READER-LABELS/release-benchmark.md; ventures/blocks/reader/samples/LABEL-PROVENANCE.md"
attempts_made: 1
status: filed
assigned_to: RG-FDA
resolution: null
resolution_evidence: null
---

The independent evaluator froze source-grounded labels and page provenance before
the unchanged benchmark ran. On seven hash-matched public PDFs, the benchmark
reported 9/13 certain fields (69.23%) and 9/12 known values matched (75.00%),
below the 95% release criterion. The GSA form's two blank fields were returned
as their printed headings with `uncertain: false`; the EPA sample's current
usage (557 kWh) was returned as null and uncertain. The frozen labels were not
changed after observing these results.

This is outside the reader-evaluator lane. The assigned RG-FDA owner
should investigate separately; this claim does not authorize changes to the
reader, benchmark, or existing checks by the evaluator.
