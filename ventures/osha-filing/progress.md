# OSHA filing preparation progress

## Drift check

1. Checkpoint: PH12.16 (V-OSHA3), OSHA filing.
2. Dependencies: PH5 and PH9 have not reached their exits. NORTHSTAR authorizes PH12 work in parallel for wave 6; this card does not mark the phase complete.
3. Defining properties and metrics: P-CONTROL / M-VERIFIED for customer-only certification and submission; P-VERIFY / M-VERIFIED for deterministic totals and cautious prospect screening; P-USABLE / M-INTERVENE for the CSV template and two owner launch steps.
4. Existing tools: the shared feed adapter, deadline tracker, rules checker, local-only filer guard, and approval nodes already cover the shared functionality. This venture composes them without adding a dependency.
5. Acceptance test: `ventures/osha-filing/tests/test_osha_filing.py` covers the CSV-to-worksheet CLI, zero-injury template, fixture-only ITA prospect screening, required deadline milestones, owner/customer approval edges, and no automated filing.

## Implemented

- Customer injury-log CSV template and parser. It counts distinct cases by category, sums days away and restriction days, rejects conflicting establishment details and duplicate case IDs, and creates the same printable customer-review worksheet. Existing JSON input remains supported.
- Local synthetic ITA CSV screening mode for offline checks. Candidate rows are separated from uncertain rows, and output explicitly says `synthetic_fixture`.
- Separate customer reminders for Jan 2–Mar 2 ITA submission and Feb 1–Apr 30 workplace posting. The worksheet and approval prompt leave signing, posting, and submission to the establishment executive.
- Corrected approval routing and step limit in the preparation flow after the real-backend walkthrough showed that approval branches skipped the worksheet command.
- README, manifest step descriptions, owner start guide, proof, and progress now distinguish the two owner launch steps from each customer's recurring signing/posting/submission action.

## Verification status

The requested OSHA test command passes: `~/w/glacier-lean/.venv/bin/python -m pytest ventures/osha-filing -q` → 13 passed. `ventures/install_all.py --only osha-filing --dry-run` validates all four flows. A disposable real Glacier backend installed the flows and ran the synthetic CSV through worksheet generation to the customer-review approval gate; the customer action was not approved or submitted.

The official OSHA ITA feed returned HTTP 403 on this card's sync attempt, so current public-data prospect screening is unverified. The fixture screen returned two synthetic candidates and two uncertain entries. The older PH12.16 proof recorded 400,288 rows, but that result is historical and not evidence of current feed reachability.

Other venture tests passed project-by-project except for one known recall-checker wording assertion covered by `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`; recall-actor's optional live canary was skipped. The repository-wide `pytest ventures -q` invocation also encountered import-path collisions, recorded in `PROOF.md`.

## Owner actions

Two launch actions remain for the owner: (1) create/connect the Jobber test account, review the first postcard and marketplace listing, and submit/publish the listing manually if desired; (2) review the first five prepared packets. Each customer establishment's executive separately checks, signs, posts Feb 1–Apr 30, and submits by Mar 2 through its own OSHA ITA account. No account creation, payment, publication, certification, posting, or filing is automated.

PH12.16 remains `todo` in NORTHSTAR; this card did not change NORTHSTAR status or evidence.
