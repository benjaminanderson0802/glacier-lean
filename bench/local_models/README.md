# Local model benchmark

Run the same ten short-answer tasks through Glacier's production `local_ai.run`
node against a local Ollama server:

```sh
cd glacier/backend
../../.venv/bin/python ../../bench/local_models/run_eval.py granite3.3:2b
```

Models run sequentially with `Answer only` enabled; the light-mode run also uses
`GLACIER_MAX_PARALLEL_RUNS=1`. The independent checker
trims outer whitespace and compares answers case-insensitively for exact equality.
The report records pass counts, the local Ollama `llama-server` runner's peak RSS, generated
tokens/second (aggregate generated tokens divided by Ollama generation time), and
individual task outputs. It prints a line after each task. Each task uses a 180
second timeout by default; set `GLACIER_LOCAL_EVAL_TIMEOUT` to change it. The benchmark calls Ollama at `GLACIER_OLLAMA_URL` or
`http://localhost:11434`; tests replace that HTTP endpoint with an in-process fake
server and do not download or require a model.

The earlier comparison run timed out on qwen3:1.7b's `sort_csv` task at 180
seconds. The timeout is scored as a failed exact match. RSS is sampled from
`llama-server` on Linux, with a Python-process fallback elsewhere; it describes
this host and is not a hardware requirement.

To reproduce the live run, pull missing models with `ollama pull MODEL`, confirm
`ollama list`, then run the command above. The script writes `RESULTS.md` beside
it unless `--results PATH` is supplied.
