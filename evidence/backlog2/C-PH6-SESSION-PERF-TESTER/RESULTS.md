# C-PH6-SESSION-PERF-TESTER results

Date: 2026-10-11. Worktree revision: `87fadd1d` (`card/gf-C-PH6-SESSION-PERF-TESTER`).

## Acceptance

The deterministic generator produced 826 Codex JSONL files totaling exactly 1,788,218,739 bytes. Every file is included in the one complete listing. Claude Code, Gemini CLI, and OpenCode roots were redirected to empty temporary directories; no real session corpus was accessed. The synthetic directory was removed automatically after the run.

- Reader-cache-cold listing: **3.590148 s**, 826 rows.
- Reader-cache-warm listing: **0.008705 s**, 826 rows.
- Additional cProfile reader-cache-cold listing: **3.285573 s**, 826 rows.
- First row: `synthetic-0000`, title `Synthetic session title 0000`, started `2026-01-01T00:00:00+00:00`, updated `2026-01-01T00:00:02+00:00`.
- All 826 returned IDs and titles were checked against the generated expectations.

“Cold” means Glacier's in-process reader caches were cleared. The generator had just written the corpus, so the OS page cache was not evicted; these measurements do not represent a guaranteed physical-disk cold start. The cProfile run is separately reported because instrumentation changes timing. The result is a measurement on this host and synthetic workload, not a claim that a five-second target is met on comparable owner hardware or a claim of improvement over a matched baseline.

## Host context

Python 3.12.3; 14 logical CPUs; 9.7 GiB memory. `uptime` load averages were 6.26/3.83/1.61 shortly before the benchmark, 7.95/5.10/2.36 during it, and 5.38/4.75/2.33 afterward. At the test start they were 6.54/4.93/2.35. This was not an idle host.

## Preservation checks

The existing Codex/session unit coverage passed, including title redaction, detail redaction, title extraction, event-derived timestamp extremes, and timestamp refresh after append. The synthetic driver also checked the exact first title and timestamp semantics while asserting complete counts on cold, warm, and profiled scans.

Command, from `glacier/backend`:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_session_mirror.py tests/test_session_mirror_more.py tests/test_session_mirror_opencode.py tests/test_session_summary_units.py
```

Result: **31 passed**, 1 Starlette/httpx deprecation warning, in 3.33 s. Full output is in `session-tests.log`.

Profile command, from `glacier/backend`:

```sh
~/w/glacier-lean/.venv/bin/python ../../evidence/backlog2/C-PH6-SESSION-PERF-TESTER/run_synthetic_profile.py
```

The driver creates the fixed temporary corpus, runs complete cold/warm scans, asserts count/title/timestamps, and writes `synthetic-cold.prof` plus `synthetic-cold-profile.txt` using Python `cProfile`/`pstats`. No implementation, session tests, existing benchmark, NORTHSTAR status, or user data was changed.

## Drift and anti-pattern review

PH6.2 is the relevant checkpoint; PH2 and PH5 remain in progress, and this is a bounded measurement rather than owner-use evidence. The work serves P-PORTABLE, P-MEMORY, P-USABLE and M-INTERVENE/M-COST as specified by the card. Existing readers and tests were reused; no index/cache or dependency was added. Review of `anti_patterns_to_detect`: this is a performance artifact only and is not presented as software progress or checkpoint completion; no status claim was changed.
