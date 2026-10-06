#!/usr/bin/env bash
# Reports which tools in Glacier's plan are installed in this Linux sandbox.
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:/usr/local/py-utils/bin:$PATH"
PY=.venv/bin/python
v(){ n=$1; shift; out=$("$@" 2>/dev/null | head -1); [ -n "$out" ] && echo "OK   $n: $out" || echo "MISS $n"; }
v python3 python3 --version
v uv uv --version
v node node --version
v npm npm --version
v git git --version
v gh gh --version
v codex codex --version
v ollama ollama --version
v opencode opencode --version
v gemini-cli gemini --version
v bifrost sh -c 'ls ~/.local/bin/bifrost* /usr/local/bin/bifrost* 2>/dev/null'
v docker docker --version
v rust/cargo cargo --version
v apprise $PY -m apprise --version
v ntfy-cli ntfy --help
v chromium sh -c 'ls /opt/pw-browsers 2>/dev/null || ls ~/.cache/ms-playwright 2>/dev/null'
for m in agent_framework dbos mcp git fastapi uvicorn websockets pytest httpx acp markitdown docling sqlite_vec apprise agent_framework_ag_ui; do
  r=$($PY -c "import importlib.metadata as m,importlib;importlib.import_module('$m');print('ok')" 2>/dev/null)
  [ "$r" = ok ] && echo "OK   py:$m" || echo "MISS py:$m"
done
for p in @xyflow/react @xterm/xterm @monaco-editor/react react-force-graph-2d playwright @assistant-ui/react @ag-ui/client; do
  [ -d glacier/web/node_modules/$p ] && echo "OK   npm:$p" || echo "MISS npm:$p"
done
