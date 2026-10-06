#!/usr/bin/env python3
"""Stand-in for `codex exec` in tests: emits a few JSONL events, writes the last message to -o, exits 1 when the
prompt contains FAIL, and fakes a signed-out CLI when it contains NOAUTH."""
import json, os, sys, time

args = sys.argv[1:]
assert args[0] == "exec" and "--json" in args, args
opt = lambda flag: args[args.index(flag) + 1] if flag in args else None
prompt = args[-1]
if "NOAUTH" in prompt:
    print("Error: Not logged in. Run `codex login`.", file=sys.stderr)
    sys.exit(1)
assert os.path.isdir(opt("-C")) and opt("-s") in ("read-only", "workspace-write"), args
msg = f"did: {prompt} [sandbox={opt('-s')} cwd={os.path.basename(opt('-C'))} model={opt('-m')}]"
for ev in ({"type": "thread.started", "thread_id": "fake"}, {"type": "turn.started"},
           {"type": "item.completed", "item": {"id": "i0", "type": "agent_message", "text": msg}}):
    print(json.dumps(ev), flush=True)
    time.sleep(float(os.environ.get("FAKE_CODEX_DELAY", "0")))
fail = "FAIL" in prompt
print(json.dumps({"type": "turn.failed", "error": {"message": "fake failure"}} if fail else {"type": "turn.completed"}), flush=True)
with open(opt("-o"), "w") as f:
    f.write(msg)
sys.exit(1 if fail else 0)
