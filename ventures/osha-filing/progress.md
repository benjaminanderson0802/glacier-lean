# OSHA filing preparation progress

## Drift check

1. Checkpoint: PH12.16 (V-OSHA3), OSHA filing.
2. Dependencies: PH5 and PH9 have not reached their exits. NORTHSTAR authorizes PH12 work in parallel for wave 6; this card does not mark the phase complete.
3. Defining properties and metrics: P-CONTROL / M-VERIFIED for customer-only certification and submission; P-VERIFY / M-VERIFIED for deterministic totals and cautious prospect screening; P-USABLE / M-INTERVENE for the CSV template and one combined owner setup/review step.
4. Existing tools: the shared feed adapter, deadline tracker, rules checker, local-only filer guard, and approval nodes already cover the shared functionality. This venture composes them without adding a dependency.
5. Acceptance test: `ventures/osha-filing/tests/test_osha_filing.py` covers the CSV-to-worksheet CLI, zero-injury template, fixture-only ITA prospect screening, required deadline milestones, owner/customer approval edges, and no automated filing.

## Implemented

- Customer injury-log CSV template and parser. It counts distinct cases by category, sums days away and restriction days, rejects conflicting establishment details and duplicate case IDs, and creates the same printable customer-review worksheet. Existing JSON input remains supported.
- Added the acceptance-facing compact CSV adapter in `scripts/filing.py`. It writes an unsigned, unsubmitted review worksheet, lists missing customer confirmations, and uses the local deadline tracker for the annual reminder.
- Local synthetic ITA CSV screening mode for offline checks. Candidate rows are separated from uncertain rows, and output explicitly says `synthetic_fixture`.
- Separate customer reminders for Jan 2–Mar 2 ITA submission and Feb 1–Apr 30 workplace posting. The worksheet and approval prompt leave signing, posting, and submission to the establishment executive.
- Corrected approval routing and step limit in the preparation flow after the real-backend walkthrough showed that approval branches skipped the worksheet command.
- README, manifest step descriptions, owner start guide, proof, and progress now distinguish the two owner launch steps from each customer's recurring signing/posting/submission action.
- Corrected the prospect screen to use OSHA's public `size` category (peak employee size) when that field is present, rather than treating annual-average employees as the size threshold.
- Added `prospects --source-csv` for an OSHA summary file downloaded locally. It records the filename, row count, establishment-ID canary, and screening totals; it does not assert that an arbitrary local file is official. The supported synthetic fixture remains labeled `synthetic_fixture`.
- Corrected the daily reminder digest to show the next filing cycle after April; on October 10, 2026 it now reports the 2027 submission and posting windows.
- Fixed render-only postcard proofs to fill the establishment name and show the local landing-page path instead of leaving template variables unresolved. The proof labels that path as unhosted.

## Verification status

- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/osha-filing -q` → **22 passed**.
- `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` → **21 passed**.
- `~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only osha-filing --dry-run` → **4 flows validated**.
- Disposable real Glacier engine: `prepare-300a` run `6e72d02ec1e5` reached `customer_review` with the fixture worksheet produced and all eight checks passing; the signing/submission gate remained waiting. `osha-daily-deadlines` run `136bb6ef71b0` completed and verified, reporting 2027 windows from the 2026-10-10 as-of date.
- Official references were checked: the ITA source page, summary data dictionary, 20–249 designated-industry page, Form 300A page, ITA FAQ, and OSHA calendar. The summary data dictionary confirms `size` is the peak-size category used by the screener.
- A fresh `osha_filing.py sync` still returns HTTP 403, `changed=false`, `rows=0`. No current public row count or live-feed canary is claimed. The local CSV route is covered with synthetic schema-shaped data only; the owner must download OSHA's current CSV through a normal browser and run the canary before prospect screening.

The venture is now **ready for owner setup**. The single owner setup/review step is listed in README and the manifest; the owner downloads the current official file and records the live canary, reviews the first five worksheets and outreach materials, and chooses whether to publish the Jobber listing. The customer's executive separately reviews, signs, posts, and submits each filing. `NORTHSTAR.yaml` PH12.16 remains `todo` because the live public-data canary has not been observed.

Other venture tests passed project-by-project except for one known recall-checker wording assertion covered by `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`; recall-actor's optional live canary was skipped. The repository-wide `pytest ventures -q` invocation also encountered import-path collisions, recorded in `PROOF.md`.

## Owner actions

One launch setup/review step remains: download the current OSHA summary CSV in a normal browser, run the local screen, review the first five prepared worksheets and outreach materials, and publish the Jobber listing only if desired. The Jobber test app is already connected. Each customer establishment's executive separately checks, signs, posts Feb 1–Apr 30, and submits by Mar 2 through its own OSHA ITA account. No payment, certification, posting, or filing is automated.

PH12.16 remains `todo` in NORTHSTAR; this card did not change NORTHSTAR status or evidence.
