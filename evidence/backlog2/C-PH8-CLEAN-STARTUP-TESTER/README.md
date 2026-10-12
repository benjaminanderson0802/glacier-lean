# C-PH8-CLEAN-STARTUP-TESTER evidence

## Drift check, recorded before evaluation

1. **Checkpoint:** PH8.1. PH7 is done and PH1 remains in progress; the card explicitly authorizes this parallel verification. No phase status changes are made.
2. **Defining properties and metrics:** P-USABLE, P-MEMORY, P-CONTROL; M-RECOVER and M-AUDIT.
3. **Existing tools:** the current GitPython vault integration and isolated PATH smoke approach are retained. No dependency or license exception is introduced.
4. **Acceptance test:** with developer Git absent from the installed backend's PATH, start the app, initialize a vault, save two note versions, then use undo and verify the original content is restored. Any startup failure must name the precise blocker; do not adopt a workaround.

## Result

No desktop installer artifact is present in this worktree, so an installer-only test could not honestly be claimed. The independent evaluator was run against the current backend source layout with the project venv, disposable `GLACIER_HOME`, disposable `HOME`, and an empty backend `PATH`:

```sh
bash desktop/C-PH8-CLEAN-STARTUP-no-git.sh \
  /home/glacier/w/glacier-lean/.venv/bin/python glacier/backend
```

It fails before `/api/health` becomes available. `glacier/backend/vault.py` imports GitPython at module load; GitPython raises `ImportError: Failed to initialize: Bad git executable` because no Git executable is on PATH. Vault initialization (`git.Repo.init`) and the note save/edit/undo requests are therefore unreachable. The full captured traceback and exit status are in [no-git-startup.log](no-git-startup.log).

The evaluator can be rerun against an extracted desktop package's bundled Python and backend directory. Its success path checks two committed note versions and verifies that `/api/memory/undo` restores the first body.

## Integrator redistribution boundary

This card adds no workaround and does not bundle Git. NORTHSTAR invariant I-10 currently allows bundled components under MIT, Apache, BSD, or MPL terms; the upstream Git project says Git is released under GPL version 2. That places a Git executable outside the currently stated bundled-component allowlist. The integrator should keep the installer from claiming clean-machine vault readiness until the owner resolves a compliant implementation or redistribution proposal. This card does not interpret whether a separate optional Git process is acceptable, change license treatment, or authorize an exception.

Sources: [NORTHSTAR.yaml invariant I-10](../../../NORTHSTAR.yaml) and the [official Git project license description](https://git-scm.com/about).

## Scope and checkpoint state

Only the independent evaluator and this evidence were added. No packaging or vault implementation, existing test, claim, signing workflow, phase status, or release state was changed. PH8.1 remains in progress.
