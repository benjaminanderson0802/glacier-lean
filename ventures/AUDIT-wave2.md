# Wave 2 independent audit

Auditor: integrator, independent of the venture/block builders. Source: `ventures/SPEC.md` as read in this worktree. This audit covers the branches merged for I2 plus the venture integrations already on the base branch; “integrated” is not a launch claim.

## Merge and test scope

Merged with `--no-ff`: `card/gf-B1`, `card/gf-V-CPSC`, and final `card/gf-V-COOP`. The wave branches `card/gf-P1`, `card/gf-P2`, `card/gf-P3`, `card/gf-V-APIFY`, and `card/gf-V-WARRANTY` had no non-empty `~/tools/cards/gf-<ID>.final.txt` marker at the initial marker check and were skipped.

The installer dry-run validated eight flows across `carpenter-goods`, `coop-postcards`, and `cpsc-prep` with `ventures/install_all.py --dry-run`. The first full venture test run and focused reader/rules rerun are recorded below. Remaining release checks and live checks could not acquire the shared heavy-job slots before the worker backstop; see `claim-ph12-22-heavy-test-lock` and `evidence/ventures/wave2-integration.md`.

## Per-venture SPEC audit

| Venture | Result | SPEC checks and owner steps |
| --- | --- | --- |
| CPSC data prep (`cpsc-prep`) | Integrated, not launch-ready | Status vocabulary uses `match`, dated `no match found in CPSC flagged tariff-code list`, or `uncertain — please check`. The importer or licensed broker reviews/certifies and submits; scripts prepare files only. The batch, first broker contract, code-page publication, mail, and payment actions are gated or test-mode only. Three owner steps are listed in `ventures/cpsc-prep/README.md`. The ruleset/field-shape mismatch and absent feed IDs are tracked in `CLM-PH12-22-CPSC-INTEGRATION-GAP`; no CPSC CSV release is supported yet. |
| Co-op claims + street postcards (`coop-postcards`) | Integrated, not launch-ready | Claim and postcard actions follow Glacier approval nodes; filing is delegated to the customer for government submissions. There are three owner steps. The release test has a stale assertion described below. Claim intake currently does not use the merged reader/deadline blocks, so evidence-file extraction and durable 60/30-day reminders are not enforced before a claim can reach its approval. Street cards render 6x4; the SPEC requires USPS EDDM flat size/weight validation, which is absent. |
| Carpenter’s goods (`carpenter-goods`) | Integrated; runtime verification pending | Listing outputs use the allowed vocabulary; publication is manual after an owner approval, and commission tracking only calculates a figure without invoicing or moving money. There are three owner steps. Existing proof says the main flow failed because the installed command cwd remained the literal `{repo}` placeholder; I added runtime normalization in the installer and will report the fresh live result below. Current comparable fixtures are synthetic, so live pricing checks are still needed. |

## Exact failures and owning work

- `ventures/blocks/reader/tests/test_acceptance.py::test_schema_extraction_disagreement_is_uncertain` failed before the integration fix: the field was `uncertain: true` but retained the first engine's disputed value (`'ABC-7'` rather than `None`). The reader implementation now blanks a disputed value while retaining its source page. The test file was not changed.
- `ventures/coop-postcards/tests/test_workflow.py::CoOpWorkflowAcceptanceTests::test_claim_requires_preapproval_and_shared_rules_pass_before_filing` expects `uncertain` with the comment “This workspace has no shared rules block yet.” The merged `ventures.blocks.rules` now exists and returns `pass` for the complete valid sample, so the assertion describes the pre-merge environment. I left the test untouched under I-04. Owner: V-COOP / integrator disposition required; do not mark the whole venture release check green while this test fails.
- The stale co-op assertion is also tracked in `CLM-PH12-22-COOP-STALE-TEST`; the test remains unchanged.
- Co-op claim intake does not invoke the document reader or deadline tracker. It checks truthy evidence references and calculates reminder dates in venture-local code. Owner: V-COOP. This is a launch gap because source-page review and durable deadline tracking are explicit SPEC requirements.
- Co-op postcards do not validate USPS EDDM flat dimensions/weight; 6x4 render-only output is not a release check. Owner: V-COOP / mail block owner B4. No live mail was sent.
- CPSC's feed registry has no `cpsc_flagged_tariff_codes`, `cpsc_rule_codes`, or `cpsc_registry_template` source IDs. I changed missing source lookups to return an uncertain/blocking result instead of an uncaught `KeyError`, and changed the default to the available `cpsc_efiling.json` ruleset. That ruleset still expects `citation_codes`, structured manufacture/lab/contact objects, and month-precision manufacture dates, while the venture sends flat fields with different names and full dates; an independent reproduction returned `fail`. Owner: V-CPSC with the feed/rules block owners. Tracked in `CLM-PH12-22-CPSC-INTEGRATION-GAP`.
- Carpenter’s goods had a recorded real-runtime failure where Glacier tried to use `<home>/workspaces/car.../{repo}` as cwd and failed with `Errno 2`. Owner: V-CARPENTER / installer integration. The I2 installer now resolves `{repo}` to the repository root, normalizes `python` to `python3`, and adds repo `PYTHONPATH`; fresh runtime result is pending.

## Launch limits

No government filing, brand-portal claim, live payment, live mail, public listing, account signup, or identity verification was performed. Real Jobber, Stripe, Etsy, Shopify, and brand-portal accounts are not configured. Any source that cannot be fetched or whose feed format/canary check alerts remains blocked. The complete backend/UI test board, feed benchmark, real Glacier dry-runs, and screenshots remain pending; no checkpoint is marked done.
