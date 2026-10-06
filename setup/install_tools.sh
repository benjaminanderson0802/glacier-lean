#!/usr/bin/env bash
# Installs the open-source worker tools and libraries for the next roadmap steps into the sandbox, then prints versions.
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:/usr/local/py-utils/bin:$PATH"
uv pip install --quiet --python .venv/bin/python apprise markitdown sqlite-vec agent-client-protocol agent-framework-ag-ui
npm install -g --silent opencode-ai @google/gemini-cli @maximhq/bifrost >/dev/null 2>&1 || npm install -g opencode-ai @google/gemini-cli @maximhq/bifrost
command -v zstd >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq zstd) >/dev/null 2>&1
command -v ollama >/dev/null || (curl -fsSL https://ollama.com/install.sh | sh) >/tmp/ollama-install.log 2>&1 || echo "ollama install failed, see /tmp/ollama-install.log"
echo "--- versions"
uv pip freeze --python .venv/bin/python | grep -iE '^(apprise|markitdown|sqlite-vec|agent-client-protocol|agent-framework-ag-ui)=='
for c in opencode gemini bifrost ollama; do printf '%s: ' $c; ($c --version 2>/dev/null || $c -v 2>/dev/null) | head -1 || echo missing; done
