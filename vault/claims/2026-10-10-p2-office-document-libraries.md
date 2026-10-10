---
id: CLM-2026-10-10-P2-OFFICE-DOC-LIBRARIES
filed_by: Codex-P2
run_id: null
node_id: null
checkpoint: PH12.2
kind: capability_gap
summary: Excel workbook and PDF form steps need review of uninstalled free libraries
evidence: "The project venv reports openpyxl, pypdf and feedparser are not installed; no workbook, RSS feed or PDF form-fill node is registered in the catalog."
attempts_made: 0
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

PH12.2 asks for Excel read/write, RSS item polling, and PDF form filling/rendering. The repository currently has no pinned runtime dependencies or runner support for these operations. The project's standard Python environment has no `openpyxl`, `feedparser`, or `pypdf` module. Do not build custom spreadsheet or PDF parsers in their place. Research maintained free/open-source options, confirm redistribution licenses and compatibility with the pinned runtime, then propose the pinned dependencies and acceptance checks. Excel, RSS, and PDF form work is parked pending that capability review; this claim does not cover the existing PDF text reader.
