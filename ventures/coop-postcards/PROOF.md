# Verification proof

The card is partially verified. The postcard flow completed in a real Glacier runtime with synthetic route data and no Lob key. Co-op claim submission remains blocked by missing shared reader/rules/deadline blocks. This is not a launch proof.

## Venture acceptance checks

```sh
.venv/bin/python -m unittest discover -s ventures/coop-postcards/tests -v
```

Result: **7 tests passed**. Coverage includes required pre-approval and evidence guards, the missing shared-rules behavior (`uncertain`, not filing-ready), 60/30-day reminder dates, November year-end timing, duplicate categories, written ad approval, homeowner-name exclusion, card rendering, and approval-gated flow structure.

## Shared block checks

```sh
heavy .venv/bin/python -m unittest ventures.blocks.mail.tests.test_mail_acceptance -v
heavy .venv/bin/python -m unittest ventures.blocks.filer.tests.test_filer_acceptance -v
.venv/bin/python -m pytest -q ventures/blocks/connectors/tests/test_connectors.py
```

Results: mail **4 passed**, filer **3 passed**, connector fixtures **11 passed**. The first two use local/mock or render-only paths. These checks do not prove the missing reader, rules, or deadline blocks.

## Install and runtime checks

```sh
.venv/bin/python ventures/install_all.py --dry-run --only coop-postcards
GLACIER_HOME=/tmp/glacier-live-OFwySr GLACIER_API=http://127.0.0.1:43149 .venv/bin/python ventures/install_all.py --only coop-postcards
heavy npm run live
```

Dry-run result: both `coop-claim-readiness` and `street-postcard-proof` validated. Real install result: both flows saved (`coop-claim-readiness` commit `6f1c2be1`; `street-postcard-proof` commit `4fa77ab7`). The disposable live run reached the approval step with a synthetic route, then completed after a local approval. All four nodes finished. The mail action returned `render_only`, address verdict `uncertain`, and `not sent; no Lob test key configured`. The run required a temporary symlink from the Glacier flow workspace to this venture folder because `install_all.py` does not stage scripts into the workspace. A fresh install therefore cannot run the scripts yet. Recorded output: [live-run.json](/home/glacier/w/workers/gf-V-COOP/evidence/ventures/coop-postcards/live-run.json).

Earlier runtime failures were corrected before that passing run: the runner image has `python3` but no `python` command, and a missing Lob secret must not import the unavailable system `keyring` package just to render locally.

## Limits

No Jobber account or app UI was connected; no brand portal or customer credentials were used; no claim was filed. No Lob test API request was made. The current mail block renders 6x4 cards, so the USPS EDDM flat size/weight check is unproven. The venture's shared reader, rules and deadline packages are absent, and the local rules adapter refuses filing until the shared rules checker is installed. The real runtime screenshot is pending at `evidence/ventures/coop-postcards/approval-review.png`.

## I2 integration update (2026-10-10)

B1's reader/rules packages and the deadline package are now present in the integration worktree. This venture still does not call the reader or deadline APIs for claim documents and reminders; see `README.md` and `../AUDIT-wave2.md`. The integrated test `test_claim_requires_preapproval_and_shared_rules_pass_before_filing` still expects the pre-merge missing-rules behavior and fails; I2 left the test untouched under I-04. The shared installer now stages venture scripts into each flow workspace, so the prior temporary-symlink smoke is historical; a fresh live rerun and screenshot remain pending the shared heavy-job slot.
