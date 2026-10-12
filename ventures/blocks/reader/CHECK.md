# Reader release check

The spec release check is at least 95% field agreement between two independent
engines on the labeled public sample set, with disagreements reported as
uncertain. Run the benchmark only after the public samples have been downloaded
and their values independently labeled:

```sh
python -m ventures.blocks.reader.benchmark ventures/blocks/reader/samples/manifest.json
```

The benchmark fails closed if fewer than two engines return a value for a
field. `read_document(path, schema=None)` remains local-first: the deterministic
parser is paired with local Ollama (`granite3.3:2b` by default); if the local
model is not available, values are retained with `uncertain: true`. Images use
Tesseract when installed and then receive the same local-model cross-check.
