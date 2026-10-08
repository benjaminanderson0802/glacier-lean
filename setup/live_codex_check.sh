#!/usr/bin/env bash
# Live check: a real Codex worker node (signed in with ChatGPT) runs on the live backend and its result lands in the vault.
API=http://localhost:8000/api
curl -s -X PUT $API/environments/codex-hello -H 'content-type: application/json' -d '{
 "id":"codex-hello","name":"Codex hello (live check)",
 "nodes":[
  {"id":"n1","type":"codex","config":{"prompt":"Create a file named hello.txt in the current folder containing exactly: Glacier says hi. Then reply with one short sentence saying what you did.","sandbox":"workspace-write"},"position":{"x":0,"y":0}},
  {"id":"n2","type":"command","config":{"cmd":"cat hello.txt","cwd":"${GLACIER_HOME:-$HOME/.glacier}/workspaces/codex-hello"},"position":{"x":260,"y":0}},
  {"id":"n3","type":"note","config":{"path":"runs/{env}-{run}.md","template":"Codex live check {run}: {summary}"},"position":{"x":520,"y":0}}
 ],
 "edges":[{"id":"e1","source":"n1","target":"n2"},{"id":"e2","source":"n2","target":"n3"}]}'
echo
RUN=$(curl -s -X POST $API/environments/codex-hello/run | python3 -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
echo "run $RUN"
for i in $(seq 1 100); do
  ST=$(curl -s $API/runs/$RUN | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "$ST" != "running" ] && break
  sleep 3
done
curl -s $API/runs/$RUN | python3 -c "
import sys,json; r=json.load(sys.stdin)
print('STATUS', r['status']); print('NODES', r['node_states'])
for k,v in r['outputs'].items(): print('---', k); print((v or '')[-600:])"
echo LIVE_DONE
