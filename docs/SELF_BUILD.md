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

`run_card.py` prints the feature run ID and API address to watch. It also installs the `self-maintenance` environment as a convenience, but it starts the feature-card run; it is not the weekly-run command. To run weekly maintenance by itself, install the configured `self-maintenance` graph through `PUT /api/environments/self-maintenance`, start it with `POST /api/environments/self-maintenance/run`, and poll `GET /api/runs/{run_id}`. Configure its command working folders and maintenance script path for the checkout being inspected before saving it.

The weekly flow checks pinned Python packages and npm packages in the web and desktop projects, confirms package licences, and runs the backend tests and screen check. Its `status_note` step saves the result to `proposals/maintenance-YYYY-MM-DD.md` in the vault as `run:<id>`. The proposal includes new tool suggestions from the MCP registry, GitHub topics, and the Ollama library, using the scanner's open-source and recent-activity filters. Each source has a 20 second limit; a source that cannot be reached is marked “could not check right now.” The tool list shows at most 10 entries, and a note over 7,500 characters is shortened by trimming tool suggestions first, then package upgrade suggestions. Suggestions are for owner review only: nothing is installed, added to requirements, or adopted. It never edits requirements, lockfiles, or project code. The owner reviews proposals; approved upgrades are made in a separate feature run and tested again.

## First live run

The first real card run was `ea0a71bb2629` on 2026-10-07. Codex completed the requested two-file change in an isolated worktree, but the acceptance commands could not find `python`, so the protected guard and test commands did not run. The run was rejected at the final human gate and nothing was merged. The requested health-check implementation is also on the guard's protected-path list.

The retry run was `22c344e628ad`. The `tools/scan/` card was not protected and the scanner tests and benchmarks passed, but the guard command kept `{guard}` and `{baseline}` literal, and the backend check still used bare `python`. The run was rejected and nothing was merged. Both run records, including diffs, approvals, timings, and exact check output, are in [the live-run evidence](../evidence/live/selfbuild_first_card.md).

## W66 practice run

W66 exercised the feature flow three times on the `tools/scan/` source-list card. Runs `96510c89fd81`, `95750a94f1f9`, and `01a859d43e5c` were all rejected and none merged. The first exposed a stale practice base in the guard comparison; the second exposed the practice checkout origin mismatch and confirmed the PDF/DOCX extras were absent from its old requirements snapshot; the third was rejected before worker approval because refresh still selected source `main` instead of the exact source HEAD. The flow now refreshes from the exact source commit and uses the practice checkout as the guard baseline. The backend tests for this fix passed (15 passed); the required full suite ended with `1 failed, 553 passed, 1 skipped, 4 warnings in 143.70s (0:02:23)`, due to a separate starter low-mode default mismatch. There is no verified merge commit, so this run does not complete PH9.2. See [detailed run evidence](../evidence/live/selfbuild_first_card.md).
