# Contributing

Contributions from people and AI workers follow [`NORTHSTAR.yaml`](NORTHSTAR.yaml) and [`GOVERNANCE.md`](GOVERNANCE.md). Keep changes tied to an existing checkpoint and use plain language in anything a Glacier user reads (I-17).

## Before changing files

1. Read `AGENTS.md`, `NORTHSTAR.yaml`, `ORCHESTRATION.yaml`, and the contract or guide named by your card.
2. Use the branch named by your card (`card/<id>`) and touch only its listed paths.
3. Write the acceptance test first, then run it and confirm that it fails for the expected reason (I-03). Do not edit the check that judges your change (I-04).
4. Use free and open-source tools. The default new-spend cap is $0; use local routes or the owner's already available official CLI route where assigned. Never add a paid or closed-source dependency (I-01).

## Checks and review

Run the relevant focused test, then the complete backend suite and applicable UI checks. From the repository root:

```sh
/workspaces/glacier-lean/.venv/bin/python -m pytest -q docs/test_governance_docs.py
(cd glacier/backend && /workspaces/glacier-lean/.venv/bin/python -m pytest -q tests)
(cd glacier/web && npm run check:ui)
```

The documentation command applies to changes in these governance documents; run the backend and UI commands when your card touches those areas or requires the full board. Also run any card-specific checks. Tests must use local fakes and must not require internet access or a real AI model.

Open a pull request to `main`. Include the checkpoint, acceptance test, exact commands and results, and any limitation. A reviewer checks scope, evidence, and policy; CI and the sandbox test board must pass before the integrator merges. Only the integrator merges cards. A worker never marks a checkpoint complete without linked test or artifact evidence.

If you encounter a stuck signal, a problem outside your lane, or an unclear requirement, follow the escalation rules in `NORTHSTAR.yaml` and file a claim. Do not keep retrying past the stated budget or silently drop the issue (I-11, I-15, I-16).
