# Wave 1 integration audit

## Scope and evidence

Merged only the finished branches listed in `/mnt/c/Users/benja/glacier-setup/cards/gf/I1-branches.txt`: B3 (customer), B4 (mail and portal filer), and B5 (read-only connectors). Platform branches and CPSC/Apify venture work were not on that list, so they were not merged. Four block packages are present; document reader, rules checker, government data feed, and deadline tracker are absent.

The current tree has no `*/venture.json`, venture flows, or Ventures view. Therefore real registration and opening the ventures view cannot succeed in this branch. `python ventures/install_all.py --dry-run` exited 2 with `venture install failed: no venture manifests found; no flows can be installed`. The requested per-venture dry-runs were also attempted: CPSC exited 2 with `venture manifest not found: cpsc-prep`; Apify exited 2 with `venture manifest not found: apify-data-tools`. Importing `customer`, `connectors`, `filer`, and `mail` from `ventures.blocks` succeeded. `python -m pytest -q ventures/tests/test_integration.py` passed (8 passed in 0.17s). The release-check and full-suite results remain queued for serialized execution.

## Spec-rule audit

- **Output vocabulary:** not verified for the venture layer because no venture flows or result adapters are integrated. The connectors return raw public API records; they must not present those as legal conclusions.
- **Government filings:** the shared portal filer requires a non-empty approval ID and records the ID with the saved confirmation. CPSC/Apify are not integrated. The venture spec requires the customer/importer or licensed broker to certify and submit CPSC registry data; no filing flow is present to test that rule.
- **Outbound approvals:** portal submissions and customer support replies require approval IDs. Stripe refunds require approval IDs. The merged mail block accepts a `test_` Lob key and gates sender/suppression policy, but its postcard request has no explicit approval ID. Checkout-session creation also has no approval ID. These need an approval gate before any outbound action is enabled beyond local/test use. Real sending was not exercised.
- **Out-of-scope ventures:** none of the five explicitly cut ventures has a manifest or flow. No tariff estimator implementation was merged; it remains on hold. This is consistent with SPEC.
- **Paid live calls:** no live paid call was made. Connector tests use synthetic fixtures; the release checks use recorded/mocked responses or local mock portals. Lob refuses non-test keys; the Stripe live check was not run. Platform account checks are pending owner credentials.
- **Owner setup length:** the README records each SPEC gate and account/setup action. Several ventures require more than the 1–2 setup steps in the owner's goal (notably Apify, Warranty, CPSC, and marketplace launches). The exact steps are not collapsed into a misleading count; no owner setup can currently be completed in Glacier because the venture UI/manifests are absent.

## Known integration gaps

1. No installable venture manifest/flow exists in the merged tree; this blocks every venture smoke test and prevents the PH12.22 exit from being demonstrated.
2. The CPSC branch exists locally but was not listed as finished; Apify has no venture branch content. Their reported flow behavior was not trusted or run.
3. Blocks README files and CHECK files describe owner setup but there are only four implemented blocks, so no CPSC/Apify dependency chain can run end to end.
4. `blocks/filer/CHECK.md` documents a unittest command; execution result is pending.
5. Outbound approvals need to cover the merged mail postcard and Stripe checkout-session functions before real external use.

The merged B4 branch includes an open claim (`vault/claims/2026-10-09-ph12-7-playwright-actionability.md`): its recorded filer check had three failures because Playwright's login-button click timed out after 8 seconds. The claim records the repeated failure and is assigned to a debugger; if the independent rerun reproduces it, I will record the exact test output without modifying the filer implementation or its judge.

## Release-check results

Pending serialized execution under `flock /tmp/glacier-heavy.lock`.
