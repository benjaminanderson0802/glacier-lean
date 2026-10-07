# Contributing

Contributions follow [`NORTHSTAR.yaml`](NORTHSTAR.yaml), [`GOVERNANCE.md`](GOVERNANCE.md), and the assigned card. Keep user-facing text plain and tied to a project goal (I-17).

## Before changing files

1. Read `AGENTS.md`, `NORTHSTAR.yaml`, `ORCHESTRATION.yaml`, and the contract or guide named by your card.
2. Work on your assigned branch and touch only the paths listed on your card.
3. Write and run the acceptance test first (I-03). Never edit, disable, or bypass the check that judges your change (I-04).
4. Use free and open-source dependencies only. Prefer an existing maintained OSI-licensed tool when it covers the need (I-01). Never add a paid or closed-source dependency.
5. Use plain words in the screen. Do not make users learn internal names or jargon (I-17).

## Checks

From the repository root, run the documentation checks, full backend suite, and screen checks with the project environment installed:

```sh
../../.venv/bin/python -m pytest -q docs/test_governance_docs.py docs/test_governance_files.py
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ../../.venv/bin/python -m pytest -q tests'
(cd glacier/web && npm run check:ui)
```

The screen check includes the theme lint. All screen colours, fonts, and radii must come only from [`glacier/web/src/theme/tokens.css`](glacier/web/src/theme/tokens.css); `npm run check:ui` must pass. Do not define these theme values elsewhere.

Run focused checks for your change as well. Do not weaken an existing check to make a change pass. The full backend suite uses a shared lock; wait for your turn. Keep tests local and independent of internet access or live AI services.

## Review

Open a pull request to `main` with the checkpoint, acceptance test, exact commands and results, and any limitations. Include the exact final output line from the full suite. For screen changes, include screenshots and compare them with the established theme. A reviewer checks scope, evidence, and policy; the integrator merges after the required checks pass.

If a problem is outside your assigned work, the requirement is unclear, or you hit a stuck signal, follow the escalation rules in `NORTHSTAR.yaml` and file a claim. Do not retry past the stated limit or silently drop the issue (I-11, I-15, I-16).
