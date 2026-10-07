# Low-resource setup

Glacier checks available hardware and tools through `GET /api/system/check`. The
response reports CPU cores, memory, free disk space, installed harness versions,
Ollama models and a recommended mode. The check uses short subprocess timeouts;
missing tools are reported without preventing setup.

Computers with 8 GB RAM or less, or 4 CPU cores or less, use `low` mode with a
recommended one parallel run. Other computers use `standard` mode. When no
model is installed, `low` mode recommends `qwen3:0.6b` (Apache-2.0, about 0.5 GB to
download, about 1 GiB in use) and `standard` mode recommends `granite3.3:2b` (Apache-2.0,
about 1.5 GB to download, about 5 GiB in use), the best result in the allowed-model evaluation.
Glacier first reuses an evaluated model you already have, then any other chat model you
installed (smallest first), so nothing is downloaded when you already have one. No evaluated
model met the target of 8/10 strict, independently checked tasks; the final
score is recorded in the model evaluation evidence. Treat this as a best-effort
default, not a model that has passed the low-resource target. See
[`evidence/live/model_choice.md`](../evidence/live/model_choice.md) for licenses,
measurements and raw outputs. If memory cannot be measured, Glacier reports it
as unknown and does not use that value to select low-resource mode. Set
`GLACIER_LOCAL_MODEL` or `GLACIER_MAX_PARALLEL_RUNS` to override the
recommendation. `GET /api/system/settings` returns these effective settings.
Hardware checks use a 60-second cache and measure disk space where
`GLACIER_HOME` points (or the current folder when it is unset).

Local AI steps default
to **Answer only**: the request asks for only the answer with zero temperature,
then removes outer whitespace, one surrounding pair of backticks or `**` marks,
and one final period on a single-line answer. Choose **Free text** when an
explanation is useful. Both styles keep Ollama's `think: false` setting.

The repeatable ten-task run on 2026-10-07 scored qwen3:0.6b 4/10, qwen3:1.7b
5/10, and granite3.3:2b 6/10 with Answer only. None reached 8/10. The 1.7b
Qwen run had one 180-second task timeout. These scores improve on the previous
strict results (1/10, 2/10 and 4/10), but they do not show that small models can
reliably handle every task. See [the full comparison](../evidence/live/model_choice.md)
and [the repeatable benchmark](../bench/local_models/README.md). Its RSS value
is sampled from Ollama's `llama-server` runner on Linux and is specific to that
host; do not use it as a hardware requirement.

To apply the recommended run limit in `runner.py`, the integrator should define a semaphore
from `threading.BoundedSemaphore` using `int(os.environ.get("GLACIER_MAX_PARALLEL_RUNS", "1"))`,
then guard its node execution with this one-line hook:

```python
with _run_semaphore: res = run_node(env_id, run_id, node, last, ws)
```
