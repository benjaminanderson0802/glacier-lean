# Glacier basics test board

Run: 2026-10-06 19:13 UTC. Passed 4 of 4.

| Test | Result | Evidence |
| --- | --- | --- |
| Workflow engine: loop + approval pause + resume after restart | PASS | builder: iteration 0 /   checker: n=1 not done -> loop back /   builder: iteration 1 /   checker: n=2 not done -> loop back /   builder: iteration 2 /   checker: n=3 done -> ask human / phase1 pending approvals: 1 state: WorkflowRunState.IDLE_WITH_PENDING_REQUESTS /  // phase2 outputs: ['human said True to: finished after 3 loops'] |
| Scheduler: crash recovery + persistent schedule | PASS | log: step 1 ran, step 2 ran, CRASH, tick, step 2 ran, step 3 ran, workflow done |
| Shared memory: vault + git + search + links + undo | PASS | memory: 3 notes = 3 git commits, keyword search found the right note, links parsed, event log has 3 entries, git revert undid the last note / Processing request of type ListToolsRequest / Processing request of type CallToolRequest / Processing request of type CallToolRequest / Processing request of type CallToolRequest / Processing request of type CallToolRequest / Processing request of type CallT |
| Screen: canvas + terminal node + editor + graph | PASS | PASS nodes=3 edges=3 terminal=true editor=true graph=true errors=none |
