# Proof — Carpenter's goods

## Acceptance checks

`/home/glacier/w/glacier-lean/.venv/bin/python -m unittest discover -s ventures/carpenter-goods/tests -v`

Expected: four tests pass. They check source-linked same-category completed sales, median pricing, uncertain/no-price behavior with missing comparisons, paid-only commission calculation, and invalid-rate rejection. Fixtures are synthetic and do not prove current market pricing.

`/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run`

Expected: both declared flows validate against the Glacier node catalog.

## Live verification

`/home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods --dry-run`

Output: both flows validated (`carpenter-prepare-listing`, `carpenter-track-commissions`).

`GLACIER_HOME=<disposable home> GLACIER_API=http://127.0.0.1:35987 /home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only carpenter-goods`

Output: both flows saved to the live Glacier API (commits `e5ea9dcb` and `df550ab0`). A real run of `carpenter-prepare-listing` did not reach the script: Glacier tried to use `<home>/workspaces/carpenter-prepare-listing/{repo}` as its working directory and failed with `Errno 2`. Claim: [CLM-PH12-20-CWD-REPO](../../vault/claims/2026-10-10-ph12-20-command-cwd-repo-placeholder.md). A screenshot was not captured; the two shared heavy-job slots were occupied while the real backend was running. The failure is recorded in the live run and claim, and does not count as a passing live-flow check.

No account setup or public listing was performed. Do not mark PH12.20 done until the runtime claim is resolved, the flow runs in real Glacier with maker-provided facts and at least three current completed-sale records, and the spec-level checks are independently reviewed.
