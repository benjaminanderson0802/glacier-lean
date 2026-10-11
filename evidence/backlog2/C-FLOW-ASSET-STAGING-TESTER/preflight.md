# C-FLOW-ASSET-STAGING-TESTER preflight

## Acceptance test, written first

From a clean disposable `GLACIER_HOME`, install the unchanged property-tax and carpenter flows, run each through the real backend, and verify each reaches its preparation node with fixture-labeled source inputs. Confirm missing or uncertain inputs produce no ready-to-file artifact. Confirm installed commands do not depend on an absolute checkout path or a manually created symlink. Retain the run IDs and outputs.

## Drift check

- **Checkpoint:** PH12.22, with supporting evidence for PH12.17 and PH12.20. PH12 is authorized to proceed in parallel; this work will not claim a phase exit.
- **Dependencies:** PH5 and PH9 are still `in_progress`; PH12's explicit parallel authorization allows starting, but does not allow marking a checkpoint done.
- **Properties and metrics:** P-VERIFY and P-LOOPS; M-VERIFIED and M-SURVIVE.
- **Existing tools:** the venture installer, real backend API, and disposable-home fixtures; no new dependency is needed.
- **Acceptance:** as written above.

## Preflight result

The required C-FLOW-ASSET-STAGING integration is absent from this checkout. `origin/glacier-final`, `card/gf-C-FLOW-ASSET-STAGING`, and this tester branch all resolve to `27abb8c41a0fb140b66e583da8a1876f0eb2b2a5`. The implementation worktree at `/home/glacier/w/workers/gf-C-FLOW-ASSET-STAGING` is also clean at that same commit.

The installer currently copies venture scripts into each disposable flow workspace via `_stage_scripts`, but `_runtime_flow` rewrites `{repo}` to `str(repo_root)`. The property-tax and carpenter preparation commands use `cwd: "{repo}"` and repository-relative script paths, so they are still bound to the checkout rather than invoking staged assets. This misses the card's prerequisite and its required no-absolute-checkout-path acceptance condition.

No backend was started and no flow was installed or run. Therefore there are no run IDs or run outputs. This preflight is not evidence that either flow passes the acceptance test.

## Next step

Wait for the C-FLOW-ASSET-STAGING implementation to be integrated, then rerun this acceptance test from a clean disposable home using the real backend. No platform or venture files were changed.
