---
id: CLM-2026-10-10-E-PH6-COLD-SESSION-LIST
filed_by: E-PH6
run_id: null
node_id: null
checkpoint: PH6.2
kind: bug
summary: Cold discovery of a large local Codex corpus still exceeds five seconds
evidence: "docs/AUDIT_FINAL.md PH6.2; evidence/E-PH6/baseline-profile.log; evidence/E-PH6/session-timing.log; evidence/E-PH6/live-api.json"
attempts_made: 1
status: filed
assigned_to: debugger
resolution: null
resolution_evidence: null
---

The initial unprofiled baseline listed 869 local sessions (822 Codex files,
1,780,040,263 bytes) in 15.796 seconds, then 0.011 seconds warm. Discovery
fully decodes every changed JSONL file even when the caller needs only metadata.

One focused change avoids formatting non-user events for list summaries, and
preserves the first meaningful title independently of the 2,000-event preview.
The existing reader checks and new title unit checks pass. It does not sample,
omit, or return partial session lists; full detail and content-version hashing
remain unchanged.

The shared machine became substantially busier during verification. A profile
of the old implementation took 195.393 seconds, including 173.973 seconds in
file readline calls and 9.708 seconds formatting event text. After the change,
a cold scan of 826 Codex files (1,788,218,739 bytes) took 180.105 seconds;
the warm scan took 0.081 seconds. These are not comparable performance trials
and do not establish a five-second cold-list result. No second speculative
repair was attempted amid the environment contention.

Re-measure on a quiet shared sandbox before selecting a further fix. Preserve
all source files, exact discovery, title cleaning, recent-event semantics,
secret redaction, and read-only access. A scalable metadata index or official
session-list adapter needs independent acceptance coverage; don't silently
hide old sessions or replace event timestamps with file modification times.
