# Live Ask check

`run_live.py` starts a real backend in a temporary `GLACIER_HOME`, then sends the same JSON body and parses the same AG-UI event stream as the Ask screen. It also calls the screen's proposal apply endpoint. The backend is stopped and the temporary home removed after each repetition.

Run the no-network check with:

```sh
cd bench/live_ask
../../.venv/bin/python -m unittest -v
../../.venv/bin/python run_live.py --dry-run
```

Run five real conversations with the standard local model setting:

```sh
../../.venv/bin/python run_live.py --runs 5 --model granite3.3:2b
```

The console output preserves every raw proposal, event result, failure, and time measurement; `--output PATH` also writes that JSON to a file when requested. `--model` sets `GLACIER_LOCAL_MODEL`; it does not override the current chat route's Codex CLI default. The report states which engine the current backend actually called.
