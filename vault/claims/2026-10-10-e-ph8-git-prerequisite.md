---
id: CLM-2026-10-10-E-PH8-GIT-PREREQUISITE
filed_by: E-PH8
run_id: null
node_id: null
checkpoint: PH8.1
kind: capability_gap
summary: Installer-only startup is not proven on a clean machine without Git; the vault requires an external Git executable.
evidence: evidence/PH8/2026-10-10/no-git.log
attempts_made: 1
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

Reproduction: `env PATH=/nonexistent ~/w/glacier-lean/.venv/bin/python -c 'import git; git.Repo.init("/tmp/glacier-ph8-no-git-probe")'` exits 1 during import with `Bad git executable`. No repository is created. `glacier/backend/vault.py` imports GitPython and calls `git.Repo.init` at startup. The Tauri resources and runtime builder contain no Git executable. The existing installed-layout and platform smoke tests inherit the host PATH, including its Git, so their success cannot establish startup using only the installer.

The loading page incorrectly said all tools were optional; E-PH8 corrected that copy to identify the existing Git prerequisite. Packaging/vault changes and independent clean-machine acceptance are still required; the phase is not done.

Search of existing claims found no resolution for this missing prerequisite. Reuse the existing Git integration if an owner-approved redistribution approach fits I-10; otherwise route a vault implementation/packaging proposal to the integrator and owner before adopting a new dependency. The current system Git is a developer-environment prerequisite, not an installer solution. This card adds no dependency and makes no license exception. Independent verification must run with developer Git absent, preserving vault commits and undo. An owner PC with Git already installed does not close this gap.
