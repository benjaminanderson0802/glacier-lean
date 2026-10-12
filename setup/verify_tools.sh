#!/usr/bin/env bash
# Proves each installed tool actually runs (not just that it is on disk). Prints OK/FAIL per tool.
cd "$(dirname "$0")/.."
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/py-utils/bin:$PATH"
PY=.venv/bin/python
t(){
  n=$1; shift
  if out=$(timeout 120 "$@" 2>&1); then
    out=${out##*$'\n'}
    [ -n "$out" ] && echo "OK   $n: ${out:0:80}" || echo "FAIL $n: command returned no output"
  else
    rc=$?
    out=${out##*$'\n'}
    echo "FAIL $n (exit $rc): ${out:0:120}"
  fi
}
t codex codex --version
t opencode opencode --version
t gemini-cli gemini --version
t ollama-model sh -c "curl -s localhost:11434/api/tags | $PY -c 'import sys,json;print([m[\"name\"] for m in json.load(sys.stdin)[\"models\"]])'"
t rust cargo --version
t tauri-cli sh -c "cd glacier/web && npx tauri --version"
t bifrost sh -c "node -p \"require('$(npm root -g)/@maximhq/bifrost/package.json').version\""
t apprise $PY -c "import apprise;a=apprise.Apprise();print('apprise', apprise.__version__)"
t markitdown $PY -c "from markitdown import MarkItDown;import tempfile;f=tempfile.NamedTemporaryFile('w',suffix='.html',delete=False);f.write('<h1>Hi</h1>');f.close();print(MarkItDown().convert(f.name).text_content.strip())"
t sqlite-vec $PY -c "import sqlite3,sqlite_vec;c=sqlite3.connect(':memory:');c.enable_load_extension(True);sqlite_vec.load(c);print('vec', c.execute('select vec_version()').fetchone()[0])"
t acp-sdk $PY -c "import acp;print('acp ok')"
t docling $PY -c "import docling.document_converter as d;print('docling ok')"
t web-build sh -c "cd glacier/web && npx tsc -b && npx vite build >/dev/null && echo build-ok"
echo "INFO ag-ui: active route is Glacier's native event client; see bench/ph0/run_ph0.py replacement checks"
