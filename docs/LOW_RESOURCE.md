# Low-resource setup

Glacier checks available hardware and tools through `GET /api/system/check`. The
response reports CPU cores, memory, free disk space, installed harness versions,
Ollama models and a recommended mode. The check uses short subprocess timeouts;
missing tools are reported without preventing setup.

Computers with 8 GB RAM or less, or 4 CPU cores or less, use `low` mode with
one parallel run. Other computers use `standard` mode. The first model reported
by `ollama list` is recommended when available; otherwise Glacier recommends
`qwen3:0.6b`. Set `GLACIER_LOCAL_MODEL` or `GLACIER_MAX_PARALLEL_RUNS` to override
the recommended model or run count. `GET /api/system/settings` returns these
effective settings.

To apply the run limit in `runner.py`, the integrator should define a semaphore
from `threading.BoundedSemaphore` using `int(os.environ.get("GLACIER_MAX_PARALLEL_RUNS", "1"))`,
then guard its node execution with this one-line hook:

```python
with _run_semaphore: res = run_node(env_id, run_id, node, last, ws)
```
