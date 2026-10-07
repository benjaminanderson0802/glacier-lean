# Claim: isolated recovery benchmark run does not merge

- kind: bug
- checkpoint: PH7.5
- evidence: `RESULTS.md`; backend log from the latest run showed the API run completed but reported `isolated: true`, `merged: false`, with note `not verified; nothing reached main, the branch is kept for inspection`.
- attempts_made: 2 benchmark runs of the isolated coding case. The second was a fresh run after adding an independent `grep -q after answer.txt` acceptance check; it produced the same unmerged result.
- status: filed

The benchmark cannot measure undo of a coding run until the isolated run verifies and merges. Stop here rather than repeatedly rerunning the same failing case. Investigate why this benchmark flow is not verified, using the successful isolated command flow in `glacier/backend/tests/test_code_undo.py` as a reference, then verify in a clean run.
