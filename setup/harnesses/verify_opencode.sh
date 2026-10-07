#!/usr/bin/env bash
set -euo pipefail

command -v opencode >/dev/null || { echo "OpenCode is not installed" >&2; exit 1; }
version="$(opencode --version)"
case "$version" in
  1.18.35) ;;
  *) echo "Expected OpenCode binary 1.18.35 (npm package @opencode-ai/cli@0.0.0-beta-17823); found: $version" >&2; exit 1 ;;
esac
opencode acp --help >/dev/null
echo "OpenCode ACP verified: $version (MIT)"
