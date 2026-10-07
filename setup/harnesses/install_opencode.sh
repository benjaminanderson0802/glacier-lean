#!/usr/bin/env bash
set -euo pipefail

# OpenCode is MIT licensed. Pin the CLI version so upgrades are deliberate.
OPENCODE_VERSION="${OPENCODE_VERSION:-1.18.35}"
npm install --global "opencode-ai@${OPENCODE_VERSION}"
