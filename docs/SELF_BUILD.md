# Glacier builds Glacier

Glacier's feature flow turns a card file into a normal Glacier run. The owner first approves the start. The Codex worker then works in an isolated Git worktree with the `workspace-write` sandbox. Its changes stay on a run branch while independent checks run.

`setup/selfbuild/run_card.py` first clones or verifies the Glacier checkout at `$GLACIER_HOME/workspaces/self-feature`. The feature flow works in a per-run isolated worktree based on that checkout. Its first required check runs `setup/selfbuild/protected_guard.py` from the main checkout and compares protected files in the run copy with the main checkout. It fails if the worker edits or deletes tests, test configuration, health checks, benchmarks, verification code, or either self-build flow. The guard also prints the list of protected paths for owner review.

The run is merged into the local checkout's main branch only after every required check passes. The merge queue serializes merges and keeps conflicting work available for review. A failed test or failed verification check leaves the work unmerged. The flow never pushes to GitHub. Pushing is a separate action that needs separate approval.

The fixed acceptance checks are ordered: protected-path guard, full backend suite, other project suites, verification benchmark, and security benchmark. The benchmark runner's exit code is the gate, with results written into the run copy. The final owner check says: “Approve only if you reviewed the protected-path list above”.

## Safety rule

I-14 says agents may tighten safety rules but may not loosen them. A worker must not alter its own acceptance checks or weaken project invariants. A proposed change to a safety rule needs a human amendment to `NORTHSTAR.yaml`; this flow does not make that amendment. The verifier reads checks from the saved flow outside the worker's worktree, and the guard itself runs from the main checkout. The isolated worktree reaches local main only after verification succeeds.

## Run a card

Save the card as a text file, then run:

```sh
python setup/selfbuild/run_card.py path/to/card.md
```

The command prints the run ID and API address to watch. It also installs the `self-maintenance` flow with the checkout path and points its command step at `setup/selfbuild/maintenance.py` in that checkout. The weekly flow checks pinned Python packages and npm packages in the web and desktop projects, confirms package licences, and runs the backend tests and screen check. The command prints one plain-language proposal, and the flow's `status_note` step saves its results to `proposals/maintenance-YYYY-MM-DD.md` in the vault as `run:<id>`. Registry failures are recorded as “could not check right now.” It never edits requirements, lockfiles, or project code. The owner reviews proposals; approved upgrades are made in a separate feature run and tested again.
