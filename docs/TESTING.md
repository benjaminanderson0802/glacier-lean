# Running the tests

## Backend suite

Install the pinned dependencies from the repository root, then run the backend suite from `glacier/backend`:

```sh
python -m pip install -r ../../setup/requirements.txt
python -m pytest -q tests -n 4
```

CI uses four pytest-xdist workers on Linux and Windows. The Windows job also prints the 15 slowest tests and the short failure report, and keeps its 240-second faulthandler timeout.

The backend tests start isolated servers with per-test temporary homes and free ports. The Linux baseline below was measured serially under the shared suite lock. The parallel trials ran directly with four workers, as required for the shared sandbox.

| Linux backend run | Result | Pytest time | Wall time |
| --- | --- | ---: | ---: |
| Serial baseline | 491 passed, 1 skipped | 10:08.82 | 19:41.37 including 9:32.55 queued for the shared lock |
| Four workers, run 1 | 491 passed, 1 skipped | 3:13.59 | 3:20.50 |
| Four workers, run 2 | 491 passed, 1 skipped | 3:06.20 | 3:12.42 |
| Four workers, run 3 | 491 passed, 1 skipped | 3:11.45 | 3:18.58 |

The median four-worker pytest time was 3:11.45, about 3.2 times faster than the serial pytest time. No test failed only in parallel, so no test or fixture required changes or xdist grouping. The only test skipped in both modes reported that SQLite vector support was unavailable.

After changing code that affects the backend, run the full suite under the shared lock:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ../../.venv/bin/python -m pytest -q tests'
```
