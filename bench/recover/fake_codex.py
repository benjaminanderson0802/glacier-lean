#!/usr/bin/env python3
"""Deterministic fake Codex CLI for local benchmark runs; not an AI model."""
import sys

print('{"type":"thread.started","thread_id":"recover-fake"}')
print('{"type":"item.completed","item":{"type":"agent_message","text":"Fake Codex completed the requested local task."}}')
sys.exit(0)
