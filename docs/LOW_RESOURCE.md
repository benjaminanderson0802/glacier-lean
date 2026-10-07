# Low-resource setup

Glacier checks available hardware and tools through `GET /api/system/check`. The
response reports CPU cores, memory, free disk space, installed harness versions,
Ollama models and a recommended mode. The check uses short subprocess timeouts;
missing tools are reported without preventing setup.

Computers with 8 GB RAM or less, or 4 CPU cores or less, use `low` mode with a
recommended one parallel run. Other computers use `standard` mode. Both modes
recommend `llama3.2:3b`, the best result in the four-model CPU evaluation and
about 2 GB to download. No evaluated model met the target of 8/10 strict,
independently checked tasks; `llama3.2:3b` scored 4/10. Treat this as the
best-effort default, not a model that has passed the low-resource target. See
[`evidence/live/model_choice.md`](../evidence/live/model_choice.md) for licenses,
measurements and raw outputs. If memory cannot be measured, Glacier reports it
as unknown and does not use that value to select low-resource mode. Set
`GLACIER_LOCAL_MODEL` or `GLACIER_MAX_PARALLEL_RUNS` to override the
recommendation. `GET /api/system/settings` returns these effective settings.
Hardware checks use a 60-second cache and measure disk space where
`GLACIER_HOME` points (or the current folder when it is unset).

To apply the recommended run limit in `runner.py`, the integrator should define a semaphore
from `threading.BoundedSemaphore` using `int(os.environ.get("GLACIER_MAX_PARALLEL_RUNS", "1"))`,
then guard its node execution with this one-line hook:

```python
with _run_semaphore: res = run_node(env_id, run_id, node, last, ws)
```
