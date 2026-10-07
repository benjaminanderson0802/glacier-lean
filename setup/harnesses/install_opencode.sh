#!/usr/bin/env bash
set -euo pipefail

# OpenCode is MIT licensed. Pin the CLI version so upgrades are deliberate.
OPENCODE_VERSION="${OPENCODE_VERSION:-0.0.0-beta-17823}"
npm install --global "@opencode-ai/cli@${OPENCODE_VERSION}"
