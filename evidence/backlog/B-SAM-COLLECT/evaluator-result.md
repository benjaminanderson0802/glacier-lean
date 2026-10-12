# B-SAM-COLLECT independent evaluation

**Result:** Pass for the frozen `acceptance-contract.md` cases exercised below.

**Method:** Used a clean inline Python fixture harness derived from the contract against `ventures/sam-amendment-alerts/scripts/collect_snapshot.py`; did not use the builder's tests as evidence. The harness used a fake request callable and temporary output directories outside the repository. Interpreter: `/home/glacier/w/glacier-lean/.venv/bin/python`. All six checks passed.

| Contract case | Observed result |
|---|---|
| Successful multipage query | Two pages at offsets 0 and 2 produced all 3 unique records. Snapshot was complete and reported the selected NAICS, UTC retrieval timestamp/date, official credential-free source URL, page count, and record count. |
| Quota error on later page | A fixture 429 on page two produced quota guidance, omitted the key from the error, and left no output snapshot. |
| Partial/malformed page | An invalid result envelope on page two failed as partial/malformed and left no output snapshot. |
| Truncation | A one-page bound while results remained failed as incomplete/truncated and left no output snapshot. |
| Missing key | No transport call occurred; the error directs the user to save the key in Glacier Settings → Secrets and retry; no output snapshot was written. |
| Secret leakage in data/errors and output metadata | A fixture record echoing the key was redacted in the persisted snapshot and its `apiKey` field was removed. A quota exception carrying the key-bearing request URL surfaced only a redacted quota message. Successful metadata matched the contract. |

Harness summary: `6/6` passed. **No live SAM.gov request, credentials, or external side effects were used.**
