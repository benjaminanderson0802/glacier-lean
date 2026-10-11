# C-PH6-SESSION-PERF-TESTER acceptance

Checkpoint: PH6.2; this is a bounded performance evaluation only. PH2 and PH5 remain in progress, so it does not establish a phase exit or owner-use evidence.

Drift check: P-PORTABLE, P-MEMORY, P-USABLE; M-INTERVENE and M-COST. Existing session readers and fixtures are reused; no index or cache implementation is added. No tool gap is identified.

Acceptance: using only a deterministic generated corpus, report the cold reader-cache and warm listing duration, exact returned session count, corpus file count/bytes, machine load, and cProfile output. Validate the generated corpus's title and event timestamp semantics, then run relevant existing session unit tests covering timestamps and redaction. Do not sample, omit, or access real session data. Report whether results meet five seconds only as a measured observation on this machine.
