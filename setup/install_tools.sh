#!/usr/bin/env bash
# Model gateway (Bifrost) is pinned when the model-gateway step is built.
# Installs the open-source worker tools and libraries for the next roadmap steps into the sandbox, then prints versions.
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:/usr/local/py-utils/bin:$PATH"
uv pip install --quiet --python .venv/bin/python apprise==2.0.1 markitdown==0.1.8 sqlite-vec==0.1.9 agent-client-protocol==0.12.1 agent-framework-ag-ui==1.5.0
npm install -g --silent opencode-ai@1.18.35 @google/gemini-cli@0.63.0 >/dev/null 2>&1 || npm install -g opencode-ai@1.18.35 @google/gemini-cli@0.63.0
command -v zstd >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq zstd) >/dev/null 2>&1
command -v ollama >/dev/null || (curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.40.0 sh) >/tmp/ollama-install.log 2>&1 || echo "ollama install failed, see /tmp/ollama-install.log"
echo "--- versions"
uv pip freeze --python .venv/bin/python | grep -iE '^(apprise|markitdown|sqlite-vec|agent-client-protocol|agent-framework-ag-ui)=='
for c in opencode gemini ollama; do printf '%s: ' $c; ($c --version 2>/dev/null || $c -v 2>/dev/null) | head -1 || echo missing; done

# ---- later-milestone tools (desktop app, documents, model gateway, screen libraries) ----
echo "--- desktop build parts"
sudo apt-get install -y -qq libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev libayatana-appindicator3-dev patchelf build-essential >/tmp/apt-tauri.log 2>&1 && echo "tauri system libs ok" || echo "tauri system libs FAILED (see /tmp/apt-tauri.log)"
command -v cargo >/dev/null || [ -x "$HOME/.cargo/bin/cargo" ] || (curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.92.0 || curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable) >/tmp/rustup.log 2>&1
export PATH="$HOME/.cargo/bin:$PATH"
cargo --version || echo "rust FAILED (see /tmp/rustup.log)"
echo "--- documents (CPU-only)"
uv pip install --quiet --python .venv/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu docling==2.70.0 >/tmp/docling.log 2>&1 \
  || uv pip install --quiet --python .venv/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu docling >>/tmp/docling.log 2>&1
uv pip freeze --python .venv/bin/python | grep -iE '^docling==' || echo "docling FAILED (see /tmp/docling.log)"
echo "--- model gateway"
npm install -g --silent @maximhq/bifrost@1.6.3 >/dev/null 2>&1; node -p "'bifrost ' + require('$(npm root -g)/@maximhq/bifrost/package.json').version" 2>/dev/null || echo "bifrost FAILED"
echo "--- screen libraries"
(cd glacier/web && npm install --save-exact --no-audit --no-fund --loglevel=error @tauri-apps/cli @tauri-apps/api @monaco-editor/react react-force-graph-2d @assistant-ui/react @ag-ui/client@0.0.59 >/tmp/npm-web.log 2>&1 && echo "screen libs ok" || echo "screen libs FAILED (see /tmp/npm-web.log)")
echo "INSTALL_DONE"
