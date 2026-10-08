# Modest hardware run

This benchmark starts the real Glacier backend twice, each time with a fresh,
temporary `GLACIER_HOME`. It uses the local Ollama service already installed on
the computer; it does not download models. Light mode uses
`qwen3:0.6b` and one parallel run. Standard mode uses `granite3.3:2b` and the
backend's standard parallel-run setting (four on the measured host).

From the repository root:

```sh
./.venv/bin/python bench/modest_hw/run.py
```

The default run performs three repetitions of each of three local-AI flows in
each mode, checks their outputs, times 2,000-note graph and keyword-search
requests, and uploads a generated 20-page PDF. It writes a readable report to
`evidence/live/modest_hardware.md` and the full raw JSON beside it. Use
`--repeat 1` for a short smoke run, `--modes light` to run one mode, `--pdf
PATH` to use a real 20-page PDF, or `--output PATH --json PATH` to save the
reports elsewhere. `--reported-cores 4` records the assigned laptop context;
the host's detected logical CPU count is recorded separately.

Backend startup, idle RSS, and run wall time are recorded. While each run is in
progress, RSS is sampled every 0.5 seconds from the backend and Linux
`llama-server` process; the reported peak is the largest combined sample.
Host CPU use is sampled over each run and shown as a percentage of all detected
logical CPUs (100% means all detected CPUs are busy).
If process RSS or CPU counters cannot be read on another operating system,
the affected measurement is reported as unknown.

The flows check for specific required details or exact categories, not writing
quality. The checks are in `test_run.py` and use no Ollama model.

```sh
./.venv/bin/python -m pytest -q bench/modest_hw/test_run.py
```
