# Feature card: list discovery sources

In `tools/scan/scan.py`, add a `--list-sources` option that prints every discovery source name and URL from `sources.yaml`, one source per line, and exits successfully without making network requests. Add a test in `tools/scan/test_scan.py` that checks the output against the configured sources and proves the normal scanner does not run.
