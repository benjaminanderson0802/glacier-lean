# Contributing

Contributions from people and AI workers follow [`NORTHSTAR.yaml`](NORTHSTAR.yaml) and [`GOVERNANCE.md`](GOVERNANCE.md). Keep changes tied to an existing checkpoint and use plain language in anything a Glacier user reads (I-17).

## Before changing files

1. Read `AGENTS.md`, `NORTHSTAR.yaml`, `ORCHESTRATION.yaml`, and the contract or guide named by your card.
2. Use the branch named by your card (`card/<id>`) and touch only its listed paths.
3. Write the acceptance test first, then run it and confirm that it fails for the expected reason (I-03). Do not edit the check that judges your change (I-04).
4. Free only by default; monthly paid cap $0. A paid or closed option is never adopted by a worker; it goes to the owner as a gap proposal (D4, I-01). Use a local route or the owner's already available official CLI route only where assigned.

## Checks and review

Run the relevant focused test, then the complete backend suite and applicable UI checks. Use the project's Python environment for `python` (for example, activate the project's virtual environment first); do not rely on a system Python. From the repository root:

```sh
python -m pytest -q docs/test_governance_docs.py
(cd glacier/backend && python -m pytest -q tests)
(cd glacier/web && npm run check:ui)
```

The documentation command applies to changes in these governance documents; run the backend and UI commands when your card touches those areas or requires the full board. The sandbox test board must pass; CI too once it can run (GitHub Actions is paused by the $0 spending limit). Also run any card-specific checks. Tests must use local fakes and must not require internet access or a real AI model.

Open a pull request to `main`. Include the checkpoint, acceptance test, exact commands and results, and any limitation. A reviewer checks scope, evidence, and policy; CI and the sandbox test board must pass before the integrator merges. Only the integrator merges cards. A worker never marks a checkpoint complete without linked test or artifact evidence.

If you encounter a stuck signal, a problem outside your lane, or an unclear requirement, follow the escalation rules in `NORTHSTAR.yaml` and file a claim. Do not keep retrying past the stated budget or silently drop the issue (I-11, I-15, I-16).
